import asyncio, os, sys, random, re
from loguru import logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.apis import XianyuApis
from core.processor import DataProcessor
from core.user_processor import UserProcessor
from utils.xianyu_utils import generate_device_id


async def heartbeat_loop(api):
    """
    💓 心跳核心逻辑：确保 Session 活跃
    """
    logger.info("✅ 后台 Session 心跳任务已激活")
    dev_id = generate_device_id()

    # 启动 5 秒后先跳第一次，让你看到状态
    await asyncio.sleep(5)

    while True:
        try:
            res = api.get_token(dev_id)
            if res and 'SUCCESS' in str(res.get('ret')):
                # 使用 SUCCESS 级别，控制台高亮显示
                logger.success(f"💓 心跳成功: Session 已续期")
            else:
                logger.warning(f"💔 心跳异常响应: {res.get('ret') if res else '无响应'}")
        except Exception as e:
            logger.error(f"⚠️ 心跳协程运行出错: {e}")

        wait_time = random.randint(180, 360)
        logger.info(f"⏳ 下次自动心跳将在 {wait_time} 秒后执行...")
        await asyncio.sleep(wait_time)


async def main_logic():
    api = XianyuApis()
    api.get_token(generate_device_id())
    asyncio.create_task(heartbeat_loop(api))

    logger.info("🚀 采集器就绪，请输入闲鱼链接开始工作。")

    while True:
        url = await asyncio.get_event_loop().run_in_executor(None, lambda: input("\n请输入链接 (q退出): ").strip())
        if url.lower() == 'q': break
        if not url: continue

        # --- 逻辑优先级调整：优先识别单个商品详情 ---
        # 只要包含 id= 且不包含 personal 路径，就判定为商品详情
        if "id=" in url and "personal" not in url:
            item_id = "".join(filter(str.isdigit, url.split('id=')[-1].split('&')[0]))
            if not item_id: continue

            logger.info(f"正在分析单个商品详情: {item_id} ...")
            res = api.get_item_info(item_id)

            if res and 'data' in res and res['data'].get('itemDO'):
                folder, item, seller = DataProcessor.parse_and_save(res, item_id)
                await DataProcessor.download_images(item, seller, folder)
                logger.success(f"✨ 详情采集成功！报告已存入: {folder}")
            else:
                ret_msg = res.get('ret', ['未知原因'])[0] if res else "连接失败"
                logger.error(f"❌ 详情采集失败: {ret_msg}")

        # --- 逻辑 B: 处理用户主页 ---
        elif "userId=" in url or "personal" in url:
            try:
                # 增强解析逻辑，确保只提取纯数字 ID
                seller_id_raw = url.split("userId=")[-1].split("&")[0]
                seller_id = "".join(filter(str.isdigit, seller_id_raw))
                if not seller_id:
                    raise ValueError("无效的卖家ID")
            except:
                logger.error("❌ 无法从链接提取有效的数字 userId，请检查链接格式。")
                continue

            logger.info(f"🔍 识别到用户主页，正在获取卖家 {seller_id} 的清单...")
            all_user_items = []
            page = 1
            while True:
                res = api.get_user_items(seller_id, page)
                items, _ = UserProcessor.parse_user_items(res)
                if not items: break
                all_user_items.extend(items)
                logger.info(f"已抓取第 {page} 页，累计 {len(all_user_items)} 个商品")
                page += 1
                await asyncio.sleep(1.5)

            folder = f"downloads/user_{seller_id}"
            UserProcessor.save_user_report(seller_id, all_user_items, folder)

        else:
            logger.warning("⚠️ 无法识别该链接类型，请确保链接包含 'id=' 或 'userId='")


if __name__ == "__main__":
    try:
        asyncio.run(main_logic())
    except KeyboardInterrupt:
        os._exit(0)