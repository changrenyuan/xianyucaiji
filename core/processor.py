import os, re, httpx, asyncio, json
from loguru import logger


class DataProcessor:
    @staticmethod
    def parse_and_save(res_data, item_id):
        data = res_data.get('data', {})
        item = data.get('itemDO', {})
        seller = data.get('sellerDO', {})

        # --- 精准字段提取 (基于你提供的 JSON) ---
        publish_time = item.get('GMT_CREATE_DATE_KEY', '未知')
        sold_price = item.get('soldPrice', item.get('price', '未知'))

        # 提取卖家等级: sellerDO -> idleFishCreditTag -> trackParams -> sellerLevel
        credit_tag = seller.get('idleFishCreditTag') or {}
        seller_level = credit_tag.get('trackParams', {}).get('sellerLevel', '未知')

        # 注册年限
        reg_day = int(seller.get('userRegDay', 0))
        reg_year = round(reg_day / 365, 1)

        # 文件夹
        title = item.get('title', 'item')
        safe_title = re.sub(r'[\\/:*?"<>|]', '', title)[:15]
        folder = f"downloads/{item_id}_{safe_title}"
        os.makedirs(folder, exist_ok=True)

        # 报告写入
        report_path = f"{folder}/详情报告.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"================ 闲鱼商品采集报告 ================\n")
            f.write(f"采集时间: {data.get('serverTime', '未知')}\n")
            f.write(f"商品链接: https://www.goofish.com/item?id={item_id}\n\n")

            f.write(f"【 1. 卖家深度信息 】\n")
            f.write(f"- 卖家昵称: {seller.get('nick')}\n")
            f.write(f"- 卖家等级: Lvl {seller_level}\n")
            f.write(f"- 所在地  : {seller.get('city', '未知')}\n")
            f.write(f"- 注册天数: {reg_day} 天 (约 {reg_year} 年)\n")
            f.write(f"- 芝麻信用: {seller.get('zhimaLevelText', '未显示')}\n")
            f.write(f"- 活跃状态: {seller.get('lastVisitTime', '未知')}\n")
            f.write(f"- 回复速度: {seller.get('replyInterval', '未知')} (率: {seller.get('replyRatio24h')})\n")
            f.write(f"- 累计卖出: {seller.get('hasSoldNumInteger', 0)} 件\n\n")

            f.write(f"【 2. 商品核心数据 】\n")
            f.write(f"- 商品标题: {title}\n")
            f.write(f"- 准确售价: {sold_price} 元\n")
            f.write(f"- 发布时间: {publish_time} (GMT)\n")
            f.write(f"- 交互数据: {item.get('browseCnt', 0)} 浏览 | {item.get('wantCnt', 0)} 想要\n")

            cpvs = item.get('cpvLabels', [])
            f.write(f"- 规格参数: " + (
                " | ".join([f"{c.get('propertyName')}:{c.get('valueName')}" for c in cpvs]) if cpvs else "无") + "\n")

            f.write(f"\n【 3. 详细描述内容 】\n")
            f.write(f"{item.get('desc')}\n")
            f.write(f"================ END OF REPORT ================\n")

        return folder, item, seller

    @staticmethod
    async def download_images(item, seller, folder):
        async with httpx.AsyncClient(verify=False) as client:
            tasks = []
            # 商品图
            for i, img in enumerate(item.get('imageInfos', [])):
                url = img.get('url', '')
                if url:
                    clean_url = re.sub(r'_\d+x\d+.*\.jpg$', '', url)
                    if clean_url.startswith("//"): clean_url = "https:" + clean_url
                    tasks.append(DataProcessor._down(client, clean_url, f"{folder}/商品图_{i + 1}.jpg"))
            # 头像
            avatar = seller.get('portraitUrl')
            if avatar:
                if avatar.startswith("//"): avatar = "https:" + avatar
                tasks.append(DataProcessor._down(client, avatar, f"{folder}/卖家头像.jpg"))
            await asyncio.gather(*tasks)

    @staticmethod
    async def _down(client, url, path):
        try:
            r = await client.get(url, timeout=20)
            if r.status_code == 200:
                with open(path, "wb") as f: f.write(r.content)
        except:
            pass