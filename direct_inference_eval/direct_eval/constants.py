from __future__ import annotations

import re

ALL_HUMAN_DIMENSIONS = sorted(
    {
        "位置",
        "环境",
        "私密性",
        "充裕度",
        "态度",
        "专业度",
        "增值服务",
        "上手难易",
        "物理舒适度",
        "生理舒适度",
        "维护情况",
        "可靠性",
        "流畅度",
        "声音",
        "画面",
        "其他感官",
        "选择多样",
        "趣味性",
        "创新性",
        "丰富度",
        "价格",
        "时长/次数",
        "熟人社交",
        "陌生社交",
        "愉悦身心",
        "体验探索",
        "二刷意愿",
        "推荐意愿",
    }
)

COMMON_LABEL_ALIASES = {
    "员工态度": "态度",
    "服务态度": "态度",
    "工作人员态度": "态度",
    "员工服务": "态度",
    "服务质量": "态度",
    "员工指导": "专业度",
    "耐心指导": "专业度",
    "员工专业度": "专业度",
    "拍照服务": "增值服务",
    "地理位置": "位置",
    "位置便利": "位置",
    "交通便利": "位置",
    "环境": "环境",
    "坏境": "环境",
    "场地环境": "环境",
    "场地空间": "充裕度",
    "空间": "充裕度",
    "空间大小": "充裕度",
    "身体舒适度": "物理舒适度",
    "身体疲劳": "物理舒适度",
    "眩晕": "生理舒适度",
    "晕眩": "生理舒适度",
    "视觉": "画面",
    "视觉效果": "画面",
    "声音效果": "声音",
    "音效": "声音",
    "游戏种类": "选择多样",
    "内容多样性": "选择多样",
    "游戏丰富度": "丰富度",
    "新鲜感": "创新性",
    "社交": "熟人社交",
    "朋友社交": "熟人社交",
    "亲子社交": "熟人社交",
    "性价比": "价格",
    "性价比感知": "价格",
    "重游意愿": "二刷意愿",
    "再访意愿": "二刷意愿",
    "再次体验意愿": "二刷意愿",
    "推荐": "推荐意愿",
}

ENGLISH_LABEL_TRANSLATIONS = {
    "staff_attitude": "态度",
    "staff_service_attitude": "态度",
    "staff_service_quality": "态度",
    "service_quality": "态度",
    "staff_patience": "专业度",
    "staff_guidance": "专业度",
    "staff_professionalism": "专业度",
    "staff_expertise": "专业度",
    "service_flexibility": "增值服务",
    "service_accommodation": "增值服务",
    "location_convenience": "位置",
    "geographic_accessibility": "位置",
    "location_findability": "位置",
    "environment_ambiance": "环境",
    "environmental_aesthetics": "环境",
    "physical_comfort": "物理舒适度",
    "equipment_weight": "物理舒适度",
    "usability": "上手难易",
    "ease_of_learning": "上手难易",
    "visual_quality": "画面",
    "immersive_realism": "画面",
    "audio_quality": "声音",
    "content_variety": "选择多样",
    "game_variety": "选择多样",
    "content_diversity": "选择多样",
    "gameplay_fun": "趣味性",
    "game_enjoyment": "趣味性",
    "playfulness": "趣味性",
    "novelty": "创新性",
    "novelty_experience": "创新性",
    "price_value": "价格",
    "value_for_money": "价格",
    "social_value": "熟人社交",
    "social_interaction": "熟人社交",
    "revisit_intention": "二刷意愿",
    "revist_intention": "二刷意愿",
    "recommendation_intention": "推荐意愿",
}

HUMAN_CATEGORIES = (
    "Installation",
    "facility service",
    "interactive service",
    "patronage intent",
    "perceived value",
    "playfulness",
    "sensory appeal",
)

_CATEGORY_CANONICAL = {category.lower(): category for category in HUMAN_CATEGORIES}

CATEGORY_KEYWORD_ALIASES: dict[str, set[str]] = {
    "Installation": {"环境价值", "便利性", "环境", "空间", "位置", "场地", "安装", "门店环境"},
    "facility service": {"设备体验", "设备", "设施", "流畅", "可靠", "维护", "舒适", "生理舒适"},
    "interactive service": {"服务体验", "服务", "态度", "专业", "增值", "工作人员"},
    "patronage intent": {"整体满意度", "满意度", "推荐", "二刷", "再访", "惠顾", "复购"},
    "perceived value": {"价格感知", "价格", "价值", "情绪价值", "时间感知", "社交", "性价比"},
    "playfulness": {"互动体验", "娱乐价值", "内容价值", "趣味", "游戏", "玩法", "创新", "丰富"},
    "sensory appeal": {"沉浸体验", "沉浸", "感官", "画面", "声音", "视觉", "听觉"},
}

P_TAG_RE = re.compile(r"</?p>", flags=re.IGNORECASE)


def normalize_dimension(dim: str) -> str:
    dim = str(dim or "").strip()
    if not dim:
        return ""
    if dim in COMMON_LABEL_ALIASES:
        return COMMON_LABEL_ALIASES[dim]
    lowered = dim.lower().replace("-", "_").replace(" ", "_")
    if lowered in ENGLISH_LABEL_TRANSLATIONS:
        return ENGLISH_LABEL_TRANSLATIONS[lowered]
    return dim


def normalize_category(category: str) -> str:
    cleaned = str(category or "").strip()
    if not cleaned:
        return ""
    return _CATEGORY_CANONICAL.get(cleaned.lower(), cleaned)


def normalize_content_key(content: str) -> str:
    without_tags = P_TAG_RE.sub("", str(content or ""))
    return "".join(without_tags.split())
