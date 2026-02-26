"""
MBTI 文本分析器：从用户自述/沟通文本推断性格维度与类型。

轻量实现，基于关键词维度打分（E/I, S/N, T/F, J/P），无 LLM、无外仓依赖。
来源思路：gozervi/zervipy LoomaCRM MBTI 分析服务，已迁入 Tatha 主仓独立使用。
"""

from typing import Dict, List

# 最小有效文本长度（字符），低于此不分析
MIN_TEXT_LENGTH = 20


class MBTITextAnalyzer:
    """MBTI 文本分析器 - 从沟通/自述内容中提取性格特征"""

    def __init__(self) -> None:
        self.keywords = {
            "E": ["团队", "分享", "讨论", "活动", "社交", "热情", "外向"],
            "I": ["独立", "思考", "安静", "专注", "深入", "内省", "独处"],
            "S": ["具体", "细节", "实际", "经验", "事实", "现在", "步骤"],
            "N": ["概念", "可能", "未来", "创新", "愿景", "理论", "模式"],
            "T": ["逻辑", "分析", "客观", "效率", "原则", "公平", "理性"],
            "F": ["感受", "价值", "和谐", "关系", "同情", "体谅", "情感"],
            "J": ["计划", "组织", "决定", "结构", "截止", "完成", "确定"],
            "P": ["灵活", "适应", "探索", "开放", "即兴", "选项", "可能"],
        }
        self.flower_mapping = {
            "INTJ": {"flower": "紫罗兰", "traits": ["深思熟虑", "独立思考", "追求完美"]},
            "ENTJ": {"flower": "向日葵", "traits": ["领导力强", "目标导向", "果断决策"]},
            "INFP": {"flower": "薰衣草", "traits": ["理想主义", "富有同情心", "创造力强"]},
            "ENFP": {"flower": "雏菊", "traits": ["热情洋溢", "富有想象力", "善于沟通"]},
            "ISTJ": {"flower": "康乃馨", "traits": ["可靠负责", "注重细节", "实事求是"]},
            "ESTJ": {"flower": "菊花", "traits": ["组织能力强", "务实高效", "遵守规则"]},
            "ISFP": {"flower": "樱花", "traits": ["温和友善", "灵活变通", "审美敏感"]},
            "ESFP": {"flower": "玫瑰", "traits": ["活力四射", "乐观开朗", "享受当下"]},
        }

    def analyze_text(self, text: str) -> Dict:
        """分析文本，返回 MBTI 类型与维度分数等。文本过短时返回默认结果。"""
        if not text or len(text.strip()) < MIN_TEXT_LENGTH:
            return self._default_result()

        t = text.strip()
        e_score, i_score = self._calculate_ei(t)
        s_score, n_score = self._calculate_sn(t)
        t_score, f_score = self._calculate_tf(t)
        j_score, p_score = self._calculate_jp(t)

        mbti_type = (
            ("E" if e_score > i_score else "I")
            + ("S" if s_score > n_score else "N")
            + ("T" if t_score > f_score else "F")
            + ("J" if j_score > p_score else "P")
        )
        confidence = self._calculate_confidence(
            abs(e_score - i_score),
            abs(s_score - n_score),
            abs(t_score - f_score),
            abs(j_score - p_score),
        )
        flower_info = self.flower_mapping.get(
            mbti_type, {"flower": "百合", "traits": ["综合特质"]}
        )

        return {
            "mbti_type": mbti_type,
            "mbti_confidence": round(confidence, 2),
            "extraversion_score": round(e_score - i_score, 2),
            "sensing_score": round(s_score - n_score, 2),
            "thinking_score": round(t_score - f_score, 2),
            "judging_score": round(j_score - p_score, 2),
            "flower_personality": flower_info["flower"],
            "flower_traits": flower_info["traits"],
            "emotional_tone": self._emotional_tone(t),
            "communication_style": self._communication_style(t),
            "keywords": self._extract_keywords(t),
            "mbti_indicators": {
                "E": e_score,
                "I": i_score,
                "S": s_score,
                "N": n_score,
                "T": t_score,
                "F": f_score,
                "J": j_score,
                "P": p_score,
            },
        }

    def _calculate_ei(self, text: str) -> tuple:
        total = sum(1 for k in self.keywords["E"] if k in text) + sum(
            1 for k in self.keywords["I"] if k in text
        ) + 1
        e = (sum(1 for k in self.keywords["E"] if k in text) / total) * 100
        i = (sum(1 for k in self.keywords["I"] if k in text) / total) * 100
        return e, i

    def _calculate_sn(self, text: str) -> tuple:
        total = sum(1 for k in self.keywords["S"] if k in text) + sum(
            1 for k in self.keywords["N"] if k in text
        ) + 1
        s = (sum(1 for k in self.keywords["S"] if k in text) / total) * 100
        n = (sum(1 for k in self.keywords["N"] if k in text) / total) * 100
        return s, n

    def _calculate_tf(self, text: str) -> tuple:
        total = sum(1 for k in self.keywords["T"] if k in text) + sum(
            1 for k in self.keywords["F"] if k in text
        ) + 1
        t = (sum(1 for k in self.keywords["T"] if k in text) / total) * 100
        f = (sum(1 for k in self.keywords["F"] if k in text) / total) * 100
        return t, f

    def _calculate_jp(self, text: str) -> tuple:
        total = sum(1 for k in self.keywords["J"] if k in text) + sum(
            1 for k in self.keywords["P"] if k in text
        ) + 1
        j = (sum(1 for k in self.keywords["J"] if k in text) / total) * 100
        p = (sum(1 for k in self.keywords["P"] if k in text) / total) * 100
        return j, p

    def _calculate_confidence(
        self, ei_diff: float, sn_diff: float, tf_diff: float, jp_diff: float
    ) -> float:
        avg = (ei_diff + sn_diff + tf_diff + jp_diff) / 4
        return max(min(avg * 2, 100), 50.0)

    def _emotional_tone(self, text: str) -> str:
        pos = ["好", "棒", "优秀", "满意", "喜欢", "感谢", "期待"]
        neg = ["不", "差", "问题", "困难", "担心", "抱歉", "遗憾"]
        p = sum(1 for w in pos if w in text)
        n = sum(1 for w in neg if w in text)
        if p > n * 1.5:
            return "positive"
        if n > p * 1.5:
            return "negative"
        return "neutral"

    def _communication_style(self, text: str) -> str:
        q = text.count("？") + text.count("?")
        if q > 3:
            return "inquiring"
        if len(text) > 500:
            return "detailed"
        if len(text) < 100:
            return "concise"
        return "balanced"

    def _extract_keywords(self, text: str) -> List[str]:
        out: List[str] = []
        for dim in self.keywords.values():
            for k in dim:
                if k in text:
                    out.append(k)
        return list(dict.fromkeys(out))[:10]

    def _default_result(self) -> Dict:
        return {
            "mbti_type": "XXXX",
            "mbti_confidence": 0.0,
            "extraversion_score": 0.0,
            "sensing_score": 0.0,
            "thinking_score": 0.0,
            "judging_score": 0.0,
            "flower_personality": "待分析",
            "flower_traits": [],
            "emotional_tone": "neutral",
            "communication_style": "unknown",
            "keywords": [],
            "mbti_indicators": {},
        }
