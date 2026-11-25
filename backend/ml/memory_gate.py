from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

GateLabel = Literal["skip", "profile", "episodic"]

INITIAL_CORPUS: list[tuple[str, GateLabel]] = [
    ("哈哈哈好的谢谢你", "skip"),
    ("明白了，帮我写一段Python快速排序代码", "skip"),
    ("今天天气怎么样，讲个笑话吧", "skip"),
    ("把上面这段文字翻译成英文", "skip"),
    ("TCP三次握手和四次挥手的区别是什么", "skip"),
    ("好的没问题，继续往下说", "skip"),
    ("帮我检查一下这段SQL语句有没有语法错误", "skip"),
    ("早上好，随便聊聊", "skip"),
    ("这个报错是什么意思怎么修", "skip"),
    ("帮我总结一下这篇文章的核心观点", "skip"),
    ("1加1等于几", "skip"),
    ("收到，辛苦啦", "skip"),
    ("我是计算机科学与技术专业的学生", "profile"),
    ("我平时写Python后端偏爱用FastAPI，不太喜欢Django", "profile"),
    ("我喝咖啡一直习惯只喝无糖冰美式", "profile"),
    ("我现在戒糖了，以后喝咖啡改喝无糖冰美式", "profile"),
    ("我是前端开发工程师，主力技术栈是React和TypeScript", "profile"),
    ("我喜欢简洁直接的回答风格，代码不要写多余废话注释", "profile"),
    ("我平时习惯早起学习，不喜欢熬夜赶工", "profile"),
    ("我对花生过敏，平时饮食偏清淡不吃重辣", "profile"),
    ("记住我叫小林，目前在广州工作", "profile"),
    ("我平时喜欢打羽毛球和看科幻小说", "profile"),
    ("我的代码缩进习惯用2个空格，变量命名偏爱简洁", "profile"),
    ("我平时喝咖啡习惯喝全糖拿铁", "profile"),
    ("下周五之前我要提交综合实习报告，这几天都在赶进度", "episodic"),
    ("最近这半个月我正在做MemoryChat个人记忆助手项目", "episodic"),
    ("明天下午三点我有一场数据库课程答辩", "episodic"),
    ("12月20日是计算机应用综合实习的截止日期", "episodic"),
    ("这周末我打算去深圳参加黑客松比赛", "episodic"),
    ("最近在准备考研复试，每天都在刷机试题", "episodic"),
    ("下周二要汇报小模型对比实验的评测结果", "episodic"),
    ("今天刚开始搭建FastAPI后端框架，准备先调通SQLite", "episodic"),
    ("这个月我的目标是把DuLeMon数据集评测跑通", "episodic"),
    ("下个月初我要去新公司报到实习", "episodic"),
]


@dataclass
class GateDecision:
    label: GateLabel
    confidence: float
    probs: dict[str, float]


class MemoryGateClassifier:
    """Plan A Small Model #1: Fast Chinese memory-worthiness 3-class classifier."""

    def __init__(self, model_path: str | Path | None = None, threshold: float = 0.45):
        self.threshold = threshold
        if model_path and Path(model_path).exists():
            self.pipeline: Pipeline = joblib.load(model_path)
        else:
            self.pipeline = self._build_pipeline()
            texts, labels = zip(*INITIAL_CORPUS)
            self.fit(list(texts), list(labels))

    @staticmethod
    def _build_pipeline() -> Pipeline:
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        analyzer="char",
                        ngram_range=(1, 3),
                        sublinear_tf=True,
                        min_df=1,
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        C=3.0,
                        class_weight="balanced",
                        max_iter=500,
                        random_state=42,
                    ),
                ),
            ]
        )

    def fit(self, texts: list[str], labels: list[GateLabel]) -> None:
        self.pipeline.fit(texts, labels)

    def predict(self, text: str) -> GateDecision:
        cleaned = (text or "").strip()
        if len(cleaned) < 4:
            return GateDecision(label="skip", confidence=1.0, probs={"skip": 1.0, "profile": 0.0, "episodic": 0.0})

        raw_probs = self.pipeline.predict_proba([cleaned])[0]
        classes = list(self.pipeline.classes_)
        prob_map = {str(cls): round(float(p), 4) for cls, p in zip(classes, raw_probs)}

        best_non_skip: GateLabel = "profile" if prob_map.get("profile", 0.0) >= prob_map.get("episodic", 0.0) else "episodic"
        non_skip_conf = prob_map.get(best_non_skip, 0.0)

        if non_skip_conf >= self.threshold and non_skip_conf > prob_map.get("skip", 0.0):
            return GateDecision(label=best_non_skip, confidence=non_skip_conf, probs=prob_map)
        return GateDecision(label="skip", confidence=prob_map.get("skip", 0.0), probs=prob_map)

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, target)
