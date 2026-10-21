# Third-party notices

- `assets/NotoSans-Regular.ttf`: Noto Sans by the Noto project, SIL Open Font License 1.1. Full license: `assets/OFL.txt`. Source: https://github.com/notofonts/noto-fonts/blob/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf .
- TEDS algorithm and cell-aware cost design: Zhong et al., PubTabNet, https://github.com/ibm-aur-nlp/PubTabNet/blob/master/src/metric.py ; upstream implementation Copyright 2020 IBM, Apache 2.0. The implementation here uses a local dataclass and RapidFuzz token distances, has no upstream multiprocessing helper, and explicitly handles `th` cells. Refer to `docs/protocol-v0.1.md` for scoring conventions; do not assume untested equivalence with every TEDS implementation.
- The AmuEval adapter targets the public `MetricBase.calculate(references, hypotheses)` interface inspected at https://github.com/amu-cai/amueval-backend . Remote registration has not been performed.

Downloaded real document data retain their source-specific status and are not relicensed by this software license. Generated synthetic training artifacts declare CC BY 4.0 separately. Test answers and source-to-test mappings belong in the organizer's private repository.
