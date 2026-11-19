-- 已有数据库增量迁移：只新增跨模块关联表，不删除、不修改现有业务表。
-- 执行前请先完成 MySQL 备份，并确认当前数据库名与 .env 中的 MYSQL_DATABASE 一致。
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sys_record_link` (
  `link_id` varchar(32) NOT NULL COMMENT '关联唯一ID',
  `pair_key` varchar(96) NOT NULL COMMENT '两端规范排序后的去重键',
  `source_module` varchar(20) NOT NULL COMMENT '来源模块：sale/lease/work/inspiration',
  `source_record_id` varchar(32) NOT NULL COMMENT '来源记录ID',
  `target_module` varchar(20) NOT NULL COMMENT '目标模块：sale/lease/work/inspiration',
  `target_record_id` varchar(32) NOT NULL COMMENT '目标记录ID',
  `relation_type` varchar(20) NOT NULL DEFAULT 'related' COMMENT '关联类型',
  `note` varchar(255) DEFAULT NULL COMMENT '关联说明',
  `creator_id` varchar(32) NOT NULL COMMENT '创建人设备ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `data_status` tinyint NOT NULL DEFAULT '1' COMMENT '数据状态：1=正常 0=已取消',
  PRIMARY KEY (`link_id`),
  UNIQUE KEY `uk_record_link_pair` (`pair_key`),
  KEY `idx_link_source` (`source_module`,`source_record_id`),
  KEY `idx_link_target` (`target_module`,`target_record_id`),
  KEY `idx_link_creator` (`creator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='跨模块记录关联表';
