"""演示数据：分类 / 商品 / 用户 / 订单 / 售后。"""
from __future__ import annotations

import asyncio

from app.storage.sqlite import product_repo
from app.storage.sqlite.repositories.user_repo import user_repo
from app.storage.sqlite.repositories.order_repo import order_repo
from app.storage.sqlite.models import ProductDTO, ProductCategoryDTO, OrderItemDTO, AfterSalesDTO
from app.security.auth import hash_password
from app.logger import setup_logging, get_logger


# ============= 分类数据 =============
CATEGORIES = [
    ("数码电子", None, 1),
    ("手机", 1, 1),
    ("耳机", 1, 2),
    ("智能穿戴", 1, 3),
    ("家居生活", None, 2),
    ("小家电", 5, 1),
    ("办公学习", None, 3),
    ("电脑外设", 7, 1),
]

# ============= 商品数据 =============
PRODUCTS = [
    {
        "sku": "PHN-001", "name": "华为 Mate 70 Pro", "category_id": 2, "brand": "华为",
        "model": "Mate 70 Pro", "price": 6999.00, "original_price": 7499.00, "stock": 120,
        "sales_count": 320, "specs": {"颜色": "曜石黑", "内存": "12+256G", "屏幕": "6.82寸",
                                       "电池": "5500mAh", "充电": "100W有线+80W无线"},
        "highlights": "麒麟 9020 旗舰芯片 / 鸿蒙系统 / 双向北斗卫星消息",
        "description": "华为年度旗舰，搭载自研麒麟 9020 处理器，性能提升 35%。"
                       "6.82 寸 LTPO 屏幕支持 1-120Hz 自适应刷新率。"
                       "超光变 XMAGE 影像系统，5000 万像素主摄 + 4800 万长焦。"
                       "支持双向北斗卫星消息，无地面网络也能发送求救信号。"
                       "5500mAh 大电池配合 100W 有线快充，30 分钟充满。",
        "package_contents": "手机 × 1 / 100W 充电器 × 1 / Type-C 数据线 × 1 / 透明保护壳 × 1 / 取卡针 × 1 / 快速入门指南 × 1",
        "warranty": "主机 1 年 / 充电器 1 年 / 电池 1 年",
        "tags": ["新品", "爆款", "5G"],
        "status": "on_sale",
    },
    {
        "sku": "PHN-002", "name": "小米 14 Ultra", "category_id": 2, "brand": "小米",
        "model": "14 Ultra", "price": 6499.00, "original_price": 6999.00, "stock": 85,
        "sales_count": 210, "specs": {"颜色": "龙晶蓝", "内存": "16+512G", "屏幕": "6.73寸",
                                       "电池": "5000mAh", "充电": "90W有线+50W无线"},
        "highlights": "徕卡四摄 / 骁龙 8 Gen3 / 双向卫星通信",
        "description": "小米与徕卡联合打造的专业影像旗舰。一英寸可变光圈主摄，"
                       "徕卡 Summilux 镜头，全焦段覆盖。"
                       "骁龙 8 Gen3 处理器搭配 LPDDR5X + UFS 4.0，安兔兔跑分超 220 万。"
                       "6.73 寸 2K LTPO 屏幕，峰值亮度 3000nit。"
                       "90W 有线秒充，5000mAh 30 分钟充满。",
        "package_contents": "手机 × 1 / 90W 充电器 × 1 / 数据线 × 1 / 保护壳 × 1 / 说明书 × 1",
        "warranty": "主机 1 年 / 电池 1 年",
        "tags": ["新品", "拍照神器", "5G"],
        "status": "on_sale",
    },
    {
        "sku": "EAR-001", "name": "AirPods Pro 3", "category_id": 3, "brand": "Apple",
        "model": "Pro 3", "price": 1899.00, "original_price": 1999.00, "stock": 200,
        "sales_count": 580, "specs": {"颜色": "白色", "续航": "6小时（单次）", "降噪": "主动降噪",
                                       "防水": "IP54"},
        "highlights": "H3 芯片 / 自适应音频 / 主动降噪 / 空间音频",
        "description": "Apple 新一代旗舰真无线耳机，搭载 H3 芯片，连接更稳定、延迟更低。"
                       "自适应音频功能根据环境自动切换降噪和通透模式。"
                       "支持空间音频和动态头部追踪，沉浸式聆听体验。"
                       "单次充电续航 6 小时，配合充电盒总续航 30 小时。"
                       "USB-C 接口支持有线充电和 Qi 无线充电。",
        "package_contents": "耳机 × 1 对 / 充电盒 × 1 / 硅胶耳塞 × 4 副 / Type-C 数据线 × 1 / 说明书 × 1",
        "warranty": "1 年保修",
        "tags": ["爆款", "降噪", "送礼"],
        "status": "on_sale",
    },
    {
        "sku": "EAR-002", "name": "索尼 WH-1000XM5", "category_id": 3, "brand": "索尼",
        "model": "WH-1000XM5", "price": 2399.00, "original_price": 2899.00, "stock": 60,
        "sales_count": 95, "specs": {"颜色": "黑色", "续航": "30小时", "降噪": "主动降噪",
                                       "重量": "250g"},
        "highlights": "业界最强降噪 / LDAC 高码率 / 30小时续航",
        "description": "索尼旗舰头戴式降噪耳机，搭载 V1 + QN1 双处理器，"
                       "8 麦克风系统，业界最强降噪水平。"
                       "支持 LDAC 高码率无线传输和 Hi-Res Audio 认证。"
                       "30mm 驱动单元，低频强劲人声细腻。"
                       "30 小时超长续航，充电 3 分钟听歌 3 小时。",
        "package_contents": "耳机 × 1 / 收纳盒 × 1 / 3.5mm 音频线 × 1 / Type-C 数据线 × 1",
        "warranty": "1 年保修",
        "tags": ["降噪", "HIFI"],
        "status": "on_sale",
    },
    {
        "sku": "WTC-001", "name": "Apple Watch Series 10", "category_id": 4, "brand": "Apple",
        "model": "S10", "price": 3199.00, "original_price": 3299.00, "stock": 150,
        "sales_count": 180, "specs": {"尺寸": "46mm", "颜色": "钛金属原色", "GPS": "蜂窝版",
                                       "续航": "18小时"},
        "highlights": "S10 芯片 / 钛金属表壳 / 全面屏设计 / 睡眠呼吸暂停检测",
        "description": "Apple Watch 第 10 代，史上最薄最轻的 Apple Watch。"
                       "钛金属表壳搭配蓝宝石玻璃镜面，坚固耐用。"
                       "S10 芯片性能提升，屏幕比上代增大 30%。"
                       "新增睡眠呼吸暂停检测、心率异常提醒等健康功能。"
                       "支持车祸检测、跌倒检测等安全功能。",
        "package_contents": "手表 × 1 / 运动表带 × 1 / 磁力充电线 × 1 / 说明书 × 1",
        "warranty": "1 年保修",
        "tags": ["新品", "送礼", "健康"],
        "status": "on_sale",
    },
    {
        "sku": "JIA-001", "name": "小米扫地机器人 X10+", "category_id": 6, "brand": "小米",
        "model": "X10+", "price": 2799.00, "original_price": 3299.00, "stock": 70,
        "sales_count": 130, "specs": {"吸力": "4000Pa", "续航": "180分钟",
                                       "功能": "扫拖一体 / 自动集尘 / 自动洗拖布"},
        "highlights": "全能基站 / 自动洗拖布 / 4000Pa 强劲吸力",
        "description": "小米全能扫拖一体机器人旗舰款。基座支持自动集尘、自动洗拖布、"
                       "自动加水、自动烘干，60 天免人工干预。"
                       "4000Pa 强劲吸力，地板缝隙灰尘也能吸净。"
                       "LDS 激光导航 + AI 视觉识别，3D 立体避障。"
                       "米家 App 远程控制，支持小爱同学语音。",
        "package_contents": "主机 × 1 / 基站 × 1 / 拖布 × 2 / 边刷 × 2 / 集尘袋 × 2 / 说明书 × 1",
        "warranty": "主机 2 年 / 电池 1 年",
        "tags": ["爆款", "智能家居", "解放双手"],
        "status": "on_sale",
    },
    {
        "sku": "JIA-002", "name": "戴森 V12 无线吸尘器", "category_id": 6, "brand": "戴森",
        "model": "V12", "price": 3990.00, "original_price": 4490.00, "stock": 40,
        "sales_count": 65, "specs": {"吸力": "150AW", "续航": "60分钟", "重量": "1.5kg",
                                       "过滤": "5重HEPA过滤"},
        "highlights": "激光显尘 / 智能感应 / 5 重 HEPA 过滤",
        "description": "戴森 V12 Detect Slim 无线吸尘器。"
                       "激光显尘技术让微小灰尘肉眼可见。"
                       "智能感应系统根据地面类型自动调节吸力。"
                       "125000 转/分钟数码马达，150AW 强劲吸力。"
                       "5 重 HEPA 过滤系统，排出洁净空气。",
        "package_contents": "主机 × 1 / 激光显尘吸头 × 1 / 多种吸头 × 5 / 充电挂架 × 1 / 说明书 × 1",
        "warranty": "主机 2 年",
        "tags": ["高端", "清洁神器"],
        "status": "on_sale",
    },
    {
        "sku": "OFC-001", "name": "罗技 MX Master 3S", "category_id": 8, "brand": "罗技",
        "model": "MX Master 3S", "price": 799.00, "original_price": 899.00, "stock": 110,
        "sales_count": 250, "specs": {"颜色": "石墨黑", "DPI": "8000", "续航": "70天",
                                       "连接": "蓝牙+USB接收器"},
        "highlights": "静音点击 / 8K DPI / 跨设备切换 / 70天续航",
        "description": "罗技旗舰办公鼠标，设计师和程序员首选。"
                       "MagSpeed 电磁滚轮，1 秒可滚动 1000 行。"
                       "8K DPI 高精度传感器，玻璃表面也能追踪。"
                       "静音点击设计，办公环境友好。"
                       "支持 3 台设备切换，Flow 跨设备文件传输。",
        "package_contents": "鼠标 × 1 / USB-C 充电线 × 1 / USB 接收器 × 1 / 说明书 × 1",
        "warranty": "1 年保修",
        "tags": ["办公", "静音"],
        "status": "on_sale",
    },
    {
        "sku": "OFC-002", "name": "HHKB Professional Hybrid Type-S 静电容键盘",
        "category_id": 8, "brand": "HHKB",
        "model": "Hybrid Type-S", "price": 2880.00, "original_price": 3280.00, "stock": 30,
        "sales_count": 45, "specs": {"布局": "60键", "轴体": "静电容", "连接": "蓝牙+USB",
                                       "键帽": "PBT"},
        "highlights": "静电容轴 / 程序员神器 / 60 键紧凑布局",
        "description": "HHKB 静电容键盘，程序员和极客的最爱。"
                       "静电容轴体，长时间打字不累。"
                       "60 键紧凑布局，去掉方向键，效率至上。"
                       "PBT 键帽，磨砂手感不打油。"
                       "蓝牙 + USB 双模，可同时连接 4 台设备。",
        "package_contents": "键盘 × 1 / USB-C 数据线 × 1 / 说明书 × 1",
        "warranty": "1 年保修",
        "tags": ["高端", "程序员", "送礼"],
        "status": "on_sale",
    },
    {
        "sku": "EAR-003", "name": "小米 Buds 5 Pro", "category_id": 3, "brand": "小米",
        "model": "Buds 5 Pro", "price": 999.00, "original_price": 1299.00, "stock": 90,
        "sales_count": 160, "specs": {"颜色": "钛光金", "续航": "8小时（单次）", "降噪": "50dB主动降噪",
                                       "防水": "IP54"},
        "highlights": "50dB 主动降噪 / 同轴三单元 / 哈曼卡顿调音",
        "description": "小米 Buds 5 Pro 旗舰真无线耳机。"
                       "同轴三单元动圈，11mm 大动圈 + 陶瓷高音单元 + 平面振膜。"
                       "50dB 主动降噪，支持自适应降噪和通透模式。"
                       "哈曼卡顿金耳朵团队调音，音质出色。"
                       "8 小时单次续航，配合充电盒 38 小时总续航。",
        "package_contents": "耳机 × 1 对 / 充电盒 × 1 / 硅胶耳塞 × 3 副 / Type-C 数据线 × 1 / 说明书 × 1",
        "warranty": "1 年保修",
        "tags": ["新品", "降噪", "性价比"],
        "status": "on_sale",
    },
]


async def main() -> None:
    setup_logging()
    log = get_logger("seed_data")

    # 1. 演示用户
    if not await user_repo.get_by_username("demo"):
        await user_repo.create("demo", hash_password("demo123"), role="user",
                                nickname="演示用户")
        log.info("创建演示用户 demo / demo123")

    # 2. 分类
    cat_id_map: dict[str, int] = {}
    existing_cats = await product_repo.list_categories()
    if not existing_cats:
        for name, parent_idx, sort in CATEGORIES:
            parent_id = cat_id_map.get(CATEGORIES[parent_idx - 1][0]) if parent_idx else None
            cid = await product_repo.create_category(name, parent_id, sort)
            cat_id_map[name] = cid
            log.info(f"创建分类：{name} (id={cid})")

    # 3. 商品
    existing_skus = set()
    for kw in ["iPhone", "Mate", "AirPods", "Buds"]:
        for p in await product_repo.search_products(keyword=kw, limit=5):
            existing_skus.add(p.sku)
    for p_data in PRODUCTS:
        if p_data["sku"] in existing_skus:
            continue
        # 修正 category_id 到实际 ID
        cat = next((c for c in CATEGORIES if c[0] == p_data.get("category_name") or
                    p_data["category_id"] == c[1]), None)
        dto = ProductDTO(**{k: v for k, v in p_data.items() if k != "category_name"})
        pid = await product_repo.create_product(dto)
        log.info(f"创建商品：{dto.name} (id={pid}, sku={dto.sku})")

    # 4. 演示订单（保留旧逻辑）
    for no, product, amount, status in [
        ("ORD20260701001", "智能音箱 Pro", 499.00, "shipped"),
        ("ORD20260702002", "蓝牙耳机 Air", 299.00, "pending"),
        ("ORD20260703003", "扫地机器人", 1299.00, "delivered"),
        ("ORD20260704004", "充电宝 20000mAh", 99.00, "refunded"),
    ]:
        existing = await order_repo.get_by_no(no)
        if not existing:
            await order_repo.create(order_no=no, product_name=product,
                                    amount=amount, status=status,
                                    address="北京市海淀区中关村大街 1 号",
                                    phone="13800000001")
            log.info(f"创建订单 {no}")

    # 5. 重建商品知识库（Qdrant 向量化）
    log.info("开始重建商品知识库...")
    try:
        from app.storage.qdrant.product_indexer import reindex_all_products
        n = await reindex_all_products()
        log.info(f"商品知识库重建完成，共索引 {n} 条")
    except Exception as e:
        log.error(f"商品知识库重建失败: {e}")

    log.info("=== 演示数据导入完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
