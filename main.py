import asyncio, os, sys, random
from loguru import logger

# 强制解决 Windows 下的导入路径问题
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.apis import XianyuApis
from core.processor import DataProcessor
from utils.xianyu_utils import generate_device_id


async def heartbeat_loop(api):
    """
    💓 心跳核心逻辑：
    只要程序不关，它每隔 3-6 分钟就会自动运行一次。
    """
    logger.info("✅ 后台 Session 心跳任务已激活")
    dev_id = generate_device_id()

    while True:
        # 随机等待，模拟真人，防止被封
        wait_time = random.randint(180, 360)
        await asyncio.sleep(wait_time)

        try:
            # 执行心跳请求
            res = api.get_token(dev_id)
            if res and 'SUCCESS' in str(res.get('ret')):
                logger.debug(f"💓 心跳成功: Session 已续期 (下次心跳在 {wait_time}秒后)")
            else:
                logger.warning(f"💔 心跳异常响应: {res.get('ret') if res else '无响应'}")
        except Exception as e:
            logger.error(f"⚠️ 心跳协程运行出错: {e}")


async def main_logic():
    # 1. 初始化接口类
    api = XianyuApis()

    # 2. 启动即刻进行第一次激活同步
    api.get_token(generate_device_id())

    # 3. 【核心】将心跳放入后台任务，不阻塞下文的 input
    asyncio.create_task(heartbeat_loop(api))

    logger.info("🚀 采集器就绪，请输入闲鱼链接开始工作。")

    while True:
        # 使用 run_in_executor 让 input 不会卡死心跳
        url = await asyncio.get_event_loop().run_in_executor(None,
                                                             lambda: input("\n请输入链接 (输入 q 退出): ").strip())

        if url.lower() == 'q':
            logger.info("退出程序中...")
            break

        # 提取 ID
        item_id = "".join(filter(str.isdigit, url.split('id=')[-1].split('&')[0]))
        if not item_id:
            logger.warning("无法从链接中提取到商品 ID，请检查链接格式。")
            continue

        logger.info(f"正在分析商品: {item_id} ...")
        res = api.get_item_info(item_id)

        if res and 'data' in res and res['data'].get('itemDO'):
            # 调用 processor.py 进行数据解析和 TXT 生成
            folder, item, seller = DataProcessor.parse_and_save(res, item_id)
            # 下载图片
            await DataProcessor.download_images(item, seller, folder)
            logger.success(f"✨ 采集成功！报告已存入: {folder}")
        else:
            ret_msg = res.get('ret', ['未知原因'])[0] if res else "连接失败"
            logger.error(f"❌ 采集失败，服务器返回: {ret_msg}")


if __name__ == "__main__":
    try:
        asyncio.run(main_logic())
    except KeyboardInterrupt:
        logger.info("程序已手动停止。")
        os._exit(0)