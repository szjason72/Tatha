"""
MBTI 职业匹配知识库：按性格类型返回适合职业、工作风格、优势与成长方向。

纯内存字典，无 DB 依赖。来源：xialing Looma-CRM MBTI 职业匹配，已迁入 Tatha 主仓；
并补全 16 型以便任意分析结果均可返回职业建议。
"""

from typing import Dict, List

# 16 型职业匹配（suitable_careers / work_style / strengths / growth_areas）
CAREER_MATCHES: Dict[str, Dict[str, List[str]]] = {
    "INTJ": {
        "suitable_careers": ["软件架构师", "数据科学家", "战略顾问", "系统分析师", "CTO"],
        "work_style": ["独立工作", "长期规划", "创新思维", "系统化思考"],
        "strengths": ["战略思维", "独立解决问题", "追求卓越", "创新能力"],
        "growth_areas": ["团队协作", "情感表达", "灵活适应"],
    },
    "ENTJ": {
        "suitable_careers": ["高管", "创业者", "项目经理", "产品经理", "管理顾问"],
        "work_style": ["领导团队", "目标导向", "快速决策", "追求效率"],
        "strengths": ["领导力", "组织能力", "战略规划", "决策果断"],
        "growth_areas": ["耐心倾听", "细节关注", "情感考虑"],
    },
    "INFP": {
        "suitable_careers": ["UX设计师", "内容创作者", "心理咨询师", "品牌策划", "产品设计"],
        "work_style": ["创意工作", "价值驱动", "灵活自主", "深度思考"],
        "strengths": ["创造力", "同理心", "价值观清晰", "适应能力"],
        "growth_areas": ["执行力", "时间管理", "批判性思维"],
    },
    "ENFP": {
        "suitable_careers": ["市场营销", "公关", "培训师", "创意总监", "用户增长"],
        "work_style": ["团队协作", "创新思维", "人际互动", "多样化工作"],
        "strengths": ["热情洋溢", "沟通能力", "创新思维", "激励他人"],
        "growth_areas": ["专注力", "完成任务", "细节管理"],
    },
    "ISTJ": {
        "suitable_careers": ["会计", "审计", "质量管理", "数据分析师", "运维工程师"],
        "work_style": ["结构化", "细节导向", "规则遵守", "可靠稳定"],
        "strengths": ["责任心强", "注重细节", "执行力强", "稳定可靠"],
        "growth_areas": ["创新思维", "灵活性", "大局观"],
    },
    "ESTJ": {
        "suitable_careers": ["运营经理", "项目经理", "生产管理", "行政管理", "销售经理"],
        "work_style": ["组织管理", "高效执行", "结果导向", "团队领导"],
        "strengths": ["组织能力", "执行力", "管理能力", "决策力"],
        "growth_areas": ["创新思维", "情感智商", "变通能力"],
    },
    "ISFP": {
        "suitable_careers": ["设计师", "艺术家", "摄影师", "美工", "手工艺人"],
        "work_style": ["创意表达", "自由灵活", "实际动手", "审美追求"],
        "strengths": ["审美能力", "灵活适应", "友善温和", "实践能力"],
        "growth_areas": ["长期规划", "理论学习", "竞争意识"],
    },
    "ESFP": {
        "suitable_careers": ["销售", "活动策划", "客服", "表演者", "培训师"],
        "work_style": ["人际互动", "活力充沛", "即兴发挥", "享受过程"],
        "strengths": ["社交能力", "乐观积极", "适应力强", "现场应变"],
        "growth_areas": ["长期规划", "深度思考", "理论学习"],
    },
    "INTP": {
        "suitable_careers": ["研究员", "算法工程师", "哲学/逻辑相关", "技术写作", "顾问"],
        "work_style": ["深度分析", "理论推演", "独立研究", "逻辑严谨"],
        "strengths": ["逻辑思维", "抽象能力", "客观分析", "创新理论"],
        "growth_areas": ["执行力", "人际沟通", "时间与计划"],
    },
    "ENTP": {
        "suitable_careers": ["创业", "产品经理", "律师", "咨询", "创新策划"],
        "work_style": ["辩论与探索", "多方案尝试", "挑战成规", "快速迭代"],
        "strengths": ["辩论与说服", "创意与变通", "抗压", "多线程"],
        "growth_areas": ["落实细节", "坚持执行", "情绪稳定性"],
    },
    "INFJ": {
        "suitable_careers": ["心理咨询", "人力资源", "写作/编辑", "社会创新", "教育"],
        "work_style": ["价值驱动", "深度共情", "长期主义", "系统关怀"],
        "strengths": ["洞察人与动机", "坚持信念", "整合信息", "助人成长"],
        "growth_areas": ["边界感", "拒绝与取舍", "现实落地"],
    },
    "ENFJ": {
        "suitable_careers": ["培训师", "HR", "公关", "教育管理", "团队教练"],
        "work_style": ["带动他人", "愿景传达", "关系建设", "激励与赋能"],
        "strengths": ["感染力", "共情与协调", "责任心", "组织凝聚力"],
        "growth_areas": ["自我边界", "接受批评", "独处与复盘"],
    },
    "ISTP": {
        "suitable_careers": ["工程师", "技工", "飞行员", "运维", "竞技/实操类"],
        "work_style": ["动手实践", "冷静应对", "工具与机制", "少废话多做事"],
        "strengths": ["动手能力", "临场应变", "客观冷静", "机械/逻辑直觉"],
        "growth_areas": ["长期规划", "情感表达", "理论抽象"],
    },
    "ESTP": {
        "suitable_careers": ["销售", "创业", "应急管理", "体育/竞技", "商务拓展"],
        "work_style": ["现场决策", "冒险与尝试", "人际斡旋", "结果导向"],
        "strengths": ["应变与胆识", "说服力", "观察细节", "行动力"],
        "growth_areas": ["长远规划", "理论沉淀", "规则与合规"],
    },
    "ISFJ": {
        "suitable_careers": ["医护", "行政", "教育", "客户支持", "档案与合规"],
        "work_style": ["细致可靠", "支持他人", "按流程办事", "维护和谐"],
        "strengths": ["责任心", "细节与记忆", "忠诚", "务实关怀"],
        "growth_areas": ["拒绝与边界", "变化适应", "自我主张"],
    },
    "ESFJ": {
        "suitable_careers": ["HR", "活动组织", "客户关系", "社区/运营", "教育"],
        "work_style": ["照顾他人", "维护氛围", "协作与仪式感", "明确角色"],
        "strengths": ["热心与体贴", "组织活动", "沟通协调", "稳定团队"],
        "growth_areas": ["接受冲突", "理性取舍", "独处与自我"],
    },
}

DEFAULT_CAREER = {
    "suitable_careers": ["可根据更详细的自述再做分析"],
    "work_style": [],
    "strengths": [],
    "growth_areas": [],
}


def get_career_match(mbti_type: str) -> Dict[str, List[str]]:
    """根据 MBTI 类型返回职业匹配信息。非标准类型或未知时返回默认说明。"""
    if not mbti_type or len(mbti_type) != 4:
        return DEFAULT_CAREER.copy()
    key = mbti_type.upper()
    return CAREER_MATCHES.get(key, DEFAULT_CAREER).copy()
