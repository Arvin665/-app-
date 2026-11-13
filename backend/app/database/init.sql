-- =============================================
-- 商办信息资产库 数据库初始化
-- MySQL 8.0 / utf8mb4 / utf8mb4_unicode_ci
-- 可直接执行；重复执行只重建当前库中的这 8 张表。
-- =============================================
CREATE DATABASE IF NOT EXISTS `mall_office_asset`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `mall_office_asset`;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `biz_personal_inspiration`;
DROP TABLE IF EXISTS `biz_work_log`;
DROP TABLE IF EXISTS `biz_tenancy_lease`;
DROP TABLE IF EXISTS `biz_property_sale`;
DROP TABLE IF EXISTS `sys_attachment`;
DROP TABLE IF EXISTS `sys_operation_log`;
DROP TABLE IF EXISTS `sys_device`;
DROP TABLE IF EXISTS `sys_invite_code`;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE `sys_invite_code` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `invite_code` char(6) NOT NULL COMMENT '6位邀请码',
  `valid_start` datetime NOT NULL COMMENT '生效时间',
  `valid_end` datetime NOT NULL COMMENT '失效时间',
  `max_use_count` int NOT NULL DEFAULT '10' COMMENT '最大使用次数',
  `used_count` int NOT NULL DEFAULT '0' COMMENT '已使用次数',
  `role_level` tinyint NOT NULL DEFAULT '2' COMMENT '权限等级：1=管理员 2=普通成员',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：1=启用 0=禁用',
  `creator_id` varchar(32) NOT NULL COMMENT '创建设备ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_invite_code` (`invite_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邀请码表';

CREATE TABLE `sys_device` (
  `device_id` varchar(32) NOT NULL COMMENT '设备唯一ID',
  `device_name` varchar(100) DEFAULT NULL COMMENT '设备名称',
  `invite_code` char(6) DEFAULT NULL COMMENT '绑定的邀请码',
  `role_level` tinyint NOT NULL DEFAULT '2' COMMENT '权限等级：1=管理员 2=普通成员',
  `bind_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '绑定时间',
  `last_online_time` datetime DEFAULT NULL COMMENT '最后在线时间',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：1=正常 0=禁用',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备用户表';

CREATE TABLE `sys_operation_log` (
  `log_id` varchar(32) NOT NULL COMMENT '日志唯一ID',
  `device_id` varchar(32) NOT NULL COMMENT '操作设备ID',
  `operation_type` varchar(20) NOT NULL COMMENT '操作类型：add/update/delete/export',
  `biz_module` varchar(20) NOT NULL COMMENT '业务模块：sale/lease/work/inspiration',
  `biz_record_id` varchar(32) DEFAULT NULL COMMENT '关联业务记录ID',
  `operation_content` text COMMENT '操作内容详情',
  `ip_address` varchar(50) DEFAULT NULL COMMENT '操作IP',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (`log_id`),
  KEY `idx_device_time` (`device_id`,`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

CREATE TABLE `sys_attachment` (
  `attach_id` varchar(32) NOT NULL COMMENT '附件唯一ID',
  `biz_id` varchar(32) NOT NULL COMMENT '关联业务记录ID',
  `biz_type` varchar(20) NOT NULL COMMENT '业务模块类型：sale/lease/work/inspiration',
  `file_name` varchar(255) NOT NULL COMMENT '原始文件名',
  `file_type` varchar(20) NOT NULL COMMENT '文件类型：image/pdf/excel/word/other',
  `file_size` bigint DEFAULT NULL COMMENT '文件大小（字节）',
  `file_url` varchar(255) NOT NULL COMMENT '云端存储地址',
  `thumbnail_url` varchar(255) DEFAULT NULL COMMENT '缩略图地址（图片类）',
  `ocr_content` longtext COMMENT 'OCR识别全文内容',
  `uploader_id` varchar(32) NOT NULL COMMENT '上传人设备ID',
  `upload_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `data_status` tinyint NOT NULL DEFAULT '1' COMMENT '数据状态：1=正常 0=已删除',
  PRIMARY KEY (`attach_id`),
  KEY `idx_biz` (`biz_id`,`biz_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公共附件表';

CREATE TABLE `biz_property_sale` (
  `record_id` varchar(32) NOT NULL COMMENT '记录唯一ID',
  `creator_id` varchar(32) NOT NULL COMMENT '创建设备ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `data_status` tinyint NOT NULL DEFAULT '1' COMMENT '数据状态：1=正常 0=已删除',
  `tags` varchar(255) DEFAULT NULL COMMENT '标签，逗号分隔',
  `ext_field_1` text COMMENT '扩展字段1（文本）',
  `ext_field_2` text COMMENT '扩展字段2（文本）',
  `ext_field_3` decimal(18,2) DEFAULT NULL COMMENT '扩展字段3（数值）',
  `ext_field_4` date DEFAULT NULL COMMENT '扩展字段4（日期）',
  `ext_field_5` int DEFAULT NULL COMMENT '扩展字段5（整数）',
  `project_name` varchar(100) NOT NULL COMMENT '项目名称',
  `district` varchar(50) NOT NULL COMMENT '所在区域，如浦东-陆家嘴',
  `address` varchar(255) DEFAULT NULL COMMENT '详细地址',
  `total_area` decimal(12,2) DEFAULT NULL COMMENT '总建筑面积（㎡）',
  `standard_floor_area` decimal(12,2) DEFAULT NULL COMMENT '标准层面积（㎡）',
  `total_floors` varchar(20) DEFAULT NULL COMMENT '总楼层',
  `property_grade` varchar(20) DEFAULT NULL COMMENT '物业等级',
  `project_feature` text COMMENT '项目核心特点',
  `deal_date` date NOT NULL COMMENT '交易时间',
  `deal_total_price` decimal(18,2) DEFAULT NULL COMMENT '交易总价（万元）',
  `deal_unit_price` decimal(12,2) DEFAULT NULL COMMENT '成交单价（元/㎡）',
  `deal_type` varchar(20) DEFAULT NULL COMMENT '交易方式',
  `deal_target` varchar(50) DEFAULT NULL COMMENT '交易标的',
  `deal_status` varchar(20) NOT NULL DEFAULT '已签约' COMMENT '交易状态',
  `seller` varchar(100) DEFAULT NULL COMMENT '原业主方',
  `buyer` varchar(100) DEFAULT NULL COMMENT '受让方（买家）',
  `buyer_purpose` varchar(50) DEFAULT NULL COMMENT '买家购置用途',
  `has_intermediary` varchar(10) DEFAULT NULL COMMENT '是否有居间',
  `main_intermediary` varchar(100) DEFAULT NULL COMMENT '主居间方',
  `joint_intermediary` varchar(255) DEFAULT NULL COMMENT '联合居间方',
  `commission_remark` text COMMENT '佣金备注（加密存储）',
  `deal_background` text COMMENT '交易背景',
  `inside_story` text COMMENT '内部趣事/传闻',
  `remark` text COMMENT '通用备注',
  PRIMARY KEY (`record_id`),
  KEY `idx_deal_date` (`deal_date`),
  KEY `idx_project_name` (`project_name`),
  KEY `idx_district` (`district`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目买卖信息表';

CREATE TABLE `biz_tenancy_lease` (
  `record_id` varchar(32) NOT NULL COMMENT '记录唯一ID',
  `creator_id` varchar(32) NOT NULL COMMENT '创建设备ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `data_status` tinyint NOT NULL DEFAULT '1' COMMENT '数据状态：1=正常 0=已删除',
  `tags` varchar(255) DEFAULT NULL COMMENT '标签，逗号分隔',
  `ext_field_1` text COMMENT '扩展字段1（文本）',
  `ext_field_2` text COMMENT '扩展字段2（文本）',
  `ext_field_3` decimal(18,2) DEFAULT NULL COMMENT '扩展字段3（数值）',
  `ext_field_4` date DEFAULT NULL COMMENT '扩展字段4（日期）',
  `ext_field_5` int DEFAULT NULL COMMENT '扩展字段5（整数）',
  `company_name` varchar(100) NOT NULL COMMENT '企业名称',
  `industry` varchar(50) DEFAULT NULL COMMENT '所属行业',
  `company_scale` varchar(50) DEFAULT NULL COMMENT '企业规模',
  `old_project` varchar(100) DEFAULT NULL COMMENT '原办公项目',
  `old_area` decimal(12,2) DEFAULT NULL COMMENT '原租赁面积（㎡）',
  `old_expire_date` date DEFAULT NULL COMMENT '原租约到期时间',
  `new_project` varchar(100) NOT NULL COMMENT '新办公项目',
  `new_area` decimal(12,2) DEFAULT NULL COMMENT '新租赁面积（㎡）',
  `floor` varchar(50) DEFAULT NULL COMMENT '所在楼层',
  `lease_type` varchar(20) NOT NULL COMMENT '租赁类型',
  `rent_price` decimal(10,2) DEFAULT NULL COMMENT '租金单价（元/㎡/天）',
  `property_fee` decimal(10,2) DEFAULT NULL COMMENT '物业费标准（元/㎡/月）',
  `rent_free_period` int DEFAULT NULL COMMENT '免租期（月）',
  `lease_term` int DEFAULT NULL COMMENT '签约年限（年）',
  `start_date` date DEFAULT NULL COMMENT '起租日期',
  `end_date` date DEFAULT NULL COMMENT '到期日期',
  `rent_increase` varchar(50) DEFAULT NULL COMMENT '租金递增',
  `main_intermediary` varchar(100) DEFAULT NULL COMMENT '主居间方',
  `joint_intermediary` varchar(255) DEFAULT NULL COMMENT '联合居间方',
  `broker_name` varchar(50) DEFAULT NULL COMMENT '经办经纪人',
  `move_reason` text COMMENT '搬迁原因',
  `company_background` text COMMENT '企业动态背景',
  `remark` text COMMENT '通用备注',
  PRIMARY KEY (`record_id`),
  KEY `idx_start_date` (`start_date`),
  KEY `idx_company_name` (`company_name`),
  KEY `idx_new_project` (`new_project`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业租赁信息表';

CREATE TABLE `biz_work_log` (
  `record_id` varchar(32) NOT NULL COMMENT '记录唯一ID',
  `creator_id` varchar(32) NOT NULL COMMENT '创建设备ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `data_status` tinyint NOT NULL DEFAULT '1' COMMENT '数据状态：1=正常 0=已删除',
  `tags` varchar(255) DEFAULT NULL COMMENT '标签，逗号分隔',
  `ext_field_1` text COMMENT '扩展字段1（文本）',
  `ext_field_2` text COMMENT '扩展字段2（文本）',
  `ext_field_3` decimal(18,2) DEFAULT NULL COMMENT '扩展字段3（数值）',
  `ext_field_4` varchar(10) DEFAULT NULL COMMENT '扩展字段4（计划执行时分，格式HH:mm，全天计划为空）',
  `ext_field_5` int DEFAULT NULL COMMENT '扩展字段5（整数）',
  `record_type` varchar(20) NOT NULL COMMENT '记录类型：每日心得/客户跟进/踩盘记录/周计划/周总结/月计划/月总结/业务规划/待办计划/每日复盘',
  `record_date` date NOT NULL COMMENT '记录日期/计划执行日期',
  `content` text NOT NULL COMMENT '记录正文/计划内容',
  `todo_items` text COMMENT '待办事项',
  `related_project` varchar(255) DEFAULT NULL COMMENT '关联项目/企业',
  `follow_status` varchar(20) DEFAULT NULL COMMENT '跟进状态',
  `is_shared` tinyint NOT NULL DEFAULT '0' COMMENT '是否共享：0=私有 1=团队共享',
  PRIMARY KEY (`record_id`),
  KEY `idx_record_date` (`record_date`),
  KEY `idx_creator_date` (`creator_id`,`record_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作记录表';

CREATE TABLE `biz_personal_inspiration` (
  `record_id` varchar(32) NOT NULL COMMENT '记录唯一ID',
  `creator_id` varchar(32) NOT NULL COMMENT '创建设备ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `data_status` tinyint NOT NULL DEFAULT '1' COMMENT '数据状态：1=正常 0=已删除',
  `tags` varchar(255) DEFAULT NULL COMMENT '自定义标签，逗号分隔',
  `ext_field_1` text COMMENT '扩展字段1（文本）',
  `ext_field_2` text COMMENT '扩展字段2（文本）',
  `ext_field_3` decimal(18,2) DEFAULT NULL COMMENT '扩展字段3（数值）',
  `ext_field_4` date COMMENT '扩展字段4（日期）',
  `ext_field_5` int DEFAULT NULL COMMENT '扩展字段5（整数）',
  `inspiration_type` varchar(20) DEFAULT NULL COMMENT '灵感类型',
  `record_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  `content` text NOT NULL COMMENT '灵感正文',
  PRIMARY KEY (`record_id`),
  KEY `idx_creator_time` (`creator_id`,`record_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人灵感角表';
