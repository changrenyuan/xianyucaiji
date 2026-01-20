import time, os, json, requests
from loguru import logger
from dotenv import load_dotenv
from utils.xianyu_utils import generate_sign


class XianyuApis:
    def __init__(self, storage_path="session_storage.json"):
        load_dotenv()
        self.storage_path = storage_path
        self.session = requests.Session()
        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'referer': 'https://www.goofish.com/',
        })
        self._load_initial_cookies()

    def _load_initial_cookies(self):
        loaded = False
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = f.read().strip()
                    if data:
                        self.session.cookies.update(json.loads(data))
                        logger.info("已载入本地持久化 Cookie")
                        loaded = True
            except:
                pass
        if not loaded:
            cookie_str = os.getenv("COOKIES_STR", "")
            for item in cookie_str.split("; "):
                if '=' in item:
                    k, v = item.split('=', 1)
                    self.session.cookies.set(k, v, domain='.goofish.com')
            logger.info("已从 .env 载入初始 Cookie")

    def _save_session(self):
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.session.cookies.get_dict(), f, indent=4)

    def _mtop_request(self, api, data_json):
        t = str(int(time.time() * 1000))
        token_val = self.session.cookies.get('_m_h5_tk', '')
        token = token_val.split('_')[0] if token_val else ""

        params = {
            'jsv': '2.7.2', 'appKey': '34839810', 't': t,
            'sign': generate_sign(t, token, data_json),
            'api': api, 'type': 'json', 'data': data_json, 'v': '1.0'
        }
        try:
            resp = self.session.get(f'https://h5api.m.goofish.com/h5/{api}/1.0/', params=params, timeout=10)
            if '_m_h5_tk' in resp.cookies: self._save_session()
            return resp.json()
        except Exception as e:
            logger.error(f"网络请求异常: {e}");
            return None

    def get_token(self, dev_id):
        return self._mtop_request('mtop.taobao.idlemessage.pc.login.token', f'{{"deviceId":"{dev_id}"}}')

    def get_item_info(self, item_id):
        return self._mtop_request('mtop.taobao.idle.pc.detail', f'{{"itemId":"{item_id}"}}')

    def get_user_items(self, seller_id, page_number=1):
        """对接你发现的最新闲鱼号列表接口"""
        payload = {
            "userId": str(seller_id),
            "pageNo": int(page_number),
            "pageSize": 20
        }
        # 必须是紧凑格式 JSON
        data_json = json.dumps(payload, separators=(',', ':'))
        return self._mtop_request('mtop.idle.web.xyh.item.list', data_json)