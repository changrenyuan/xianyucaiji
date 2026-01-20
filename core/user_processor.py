import os
from loguru import logger


class UserProcessor:
    @staticmethod
    def parse_user_items(res_data):
        """精准解析 mtop.idle.web.xyh.item.list 返回的嵌套报文"""
        if not res_data or 'data' not in res_data:
            return [], 0

        data = res_data.get('data', {})
        card_list = data.get('cardList', [])

        items_list = []
        for card in card_list:
            card_data = card.get('cardData', {})
            detail = card_data.get('detailParams', {})

            if not detail: continue

            item_info = {
                'title': detail.get('title', '无标题'),
                'itemId': detail.get('itemId'),
                'price': detail.get('soldPrice', '0'),
                'wantCnt': "0人想要"
            }

            # 从 tagList 中提取人气信息
            try:
                tags = card_data.get('itemLabelDataVO', {}).get('labelData', {}).get('r3', {}).get('tagList', [])
                if tags:
                    item_info['wantCnt'] = tags[0].get('data', {}).get('content', '0人想要')
            except:
                pass

            items_list.append(item_info)

        return items_list, 999  # 该接口不直观返回总数，由 main.py 根据数据空否判断结束

    @staticmethod
    def save_user_report(seller_id, all_items, folder):
        os.makedirs(folder, exist_ok=True)
        report_path = f"{folder}/卖家_{seller_id}_在售清单.txt"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"卖家ID: {seller_id} | 累计商品: {len(all_items)}\n")
            f.write("=" * 60 + "\n\n")
            for item in all_items:
                f.write(f"【{item['title']}】\n")
                f.write(f"价格: {item['price']} 元 | 人气: {item['wantCnt']}\n")
                f.write(f"链接: https://www.goofish.com/item?id={item['itemId']}\n")
                f.write("-" * 40 + "\n")
        logger.success(f"✅ 清单导出成功: {report_path}")