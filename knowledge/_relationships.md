# 关系类型定义

## FILES_REPORT
- 描述: 向媒体反映或报案
- 来源→目标: [{'source': 'Parent', 'target': 'MediaOutlet'}, {'source': 'Parent', 'target': 'PoliceAgency'}]

## INVESTIGATES
- 描述: 公安机关侦查案件
- 来源→目标: [{'source': 'PoliceAgency', 'target': 'Suspect'}]

## PROSECUTES
- 描述: 检察院审查起诉
- 来源→目标: [{'source': 'Procuratorate', 'target': 'Suspect'}]

## REPORTS_ON
- 描述: 媒体报道事件
- 来源→目标: [{'source': 'MediaOutlet', 'target': 'Suspect'}, {'source': 'MediaOutlet', 'target': 'Victim'}]

## POSTS_OPINION
- 描述: 网民发表观点评论
- 来源→目标: [{'source': 'Person', 'target': 'Suspect'}, {'source': 'Person', 'target': 'MediaOutlet'}]

## ISSUES_GUIDANCE
- 描述: 最高检发布指导性文件
- 来源→目标: [{'source': 'SupremeProcuratorate', 'target': 'Procuratorate'}]

## EMPLOYS
- 描述: 雇佣关系
- 来源→目标: [{'source': 'Court', 'target': 'Suspect'}]

## PROTECTS
- 描述: 保护未成年人权益
- 来源→目标: [{'source': 'Organization', 'target': 'Victim'}]

