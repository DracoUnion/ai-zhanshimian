"""演示风格模板种子数据（对应 PRD V2.0 风格模板库 P1）。启动时自动填充（SEED_DEMO_TEMPLATES=true）。"""
from __future__ import annotations

from sqlalchemy import func, select

from app.config import get_settings
from app.db.session import SessionLocal
from app.models.template import Template

settings = get_settings()

DEMO_TEMPLATES = [
    {"name": "海边氛围", "category": "life", "prompt_template": "海边日落，宽松白衬衫，肩部以上半身照，柔和暖光，氛围感人像，突出自然感", "prompt_tips": "适合营造松弛、阳光的初印象", "sort": 1},
    {"name": "咖啡厅", "category": "cafe", "prompt_template": "窗边咖啡厅，慵懒午后，针织衫，半身照，胶卷色调，氛围感人像", "prompt_tips": "文艺、安静，适合读书人设", "sort": 2},
    {"name": "健身房", "category": "sport", "prompt_template": "简洁健身房，运动背心，干练，半身照，冷调光线，有力量感但不夸张", "prompt_tips": "自律、健康导向", "sort": 3},
    {"name": "城市街景", "category": "street", "prompt_template": "夜晚城市街道，霓虹灯，皮衣或夹克，半身照，电影感，时尚都市风", "prompt_tips": "潮流、都市感", "sort": 4},
    {"name": "商务简约", "category": "work", "prompt_template": "简约办公室或傍晚写字楼，白衬衫或深色西装，轻度商务，干净背景，专业感肖像", "prompt_tips": "成熟、可信、稳重", "sort": 5},
]


def seed_templates() -> None:
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Template))
        if count:
            return
        for t in DEMO_TEMPLATES:
            db.add(Template(**t))
        db.commit()
        print(f"[seed] 写入 {len(DEMO_TEMPLATES)} 个演示模板")


if __name__ == "__main__":
    seed_templates()