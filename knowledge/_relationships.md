# 关系类型定义

## REPORTS_ON
- 描述: 媒体或记者对事件进行新闻报道
- 来源→目标: [{'source': 'MediaOutlet', 'target': 'GovernmentAgency'}, {'source': 'Journalist', 'target': 'GovernmentAgency'}]

## FILES_REPORT
- 描述: 当事人或家属向相关部门报案
- 来源→目标: [{'source': 'Parent', 'target': 'GovernmentAgency'}]

## INVESTIGATES
- 描述: 公安机关对案件进行调查
- 来源→目标: [{'source': 'GovernmentAgency', 'target': 'GovernmentOfficial'}]

## PROSECUTES
- 描述: 检察院对案件进行审查起诉
- 来源→目标: [{'source': 'GovernmentAgency', 'target': 'GovernmentOfficial'}]

## COMMENTS_ON
- 描述: 网民或自媒体对事件发表观点评论
- 来源→目标: [{'source': 'Netizen', 'target': 'GovernmentAgency'}, {'source': 'PublicAccount', 'target': 'GovernmentAgency'}]

## WORKS_FOR
- 描述: 个人在某个机构工作
- 来源→目标: [{'source': 'GovernmentOfficial', 'target': 'GovernmentAgency'}]

## AFFILIATED_WITH
- 描述: 个人与某机构存在隶属或关联关系
- 来源→目标: [{'source': 'Journalist', 'target': 'MediaOutlet'}]

## REPRESENTS
- 描述: 媒体或账号代表某主体发声
- 来源→目标: [{'source': 'MediaOutlet', 'target': 'Person'}]

## PROTECTS
- 描述: 相关部门或个人保护未成年人权益
- 来源→目标: [{'source': 'GovernmentAgency', 'target': 'Minor'}]

## IS_GUARDIAN_OF
- 描述: 监护人代表未成年人利益
- 来源→目标: [{'source': 'Parent', 'target': 'Minor'}]

