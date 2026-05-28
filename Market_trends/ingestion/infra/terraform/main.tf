terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "eg-market-trends"
}

variable "lakehouse_bucket" {
  type    = string
  default = "eg-lakehouse"
}

# --- S3 bronze lakehouse bucket ---

resource "aws_s3_bucket" "lakehouse" {
  bucket = var.lakehouse_bucket
}

resource "aws_s3_bucket_versioning" "lakehouse" {
  bucket = aws_s3_bucket.lakehouse.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "lakehouse_bronze" {
  bucket = aws_s3_bucket.lakehouse.id

  rule {
    id     = "bronze-to-glacier"
    status = "Enabled"
    filter {
      prefix = "bronze/"
    }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# --- ECR repositories ---

resource "aws_ecr_repository" "ingestion" {
  name                 = "${var.project}-ingestion"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_ecr_repository" "ingestion_playwright" {
  name                 = "${var.project}-ingestion-playwright"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

# --- ECS cluster ---

resource "aws_ecs_cluster" "ingestion" {
  name = "${var.project}-cluster"
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.project}-ecs-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.project}-s3-bronze"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.lakehouse.arn,
          "${aws_s3_bucket.lakehouse.arn}/bronze/*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
      },
    ]
  })
}

locals {
  cadence_groups = {
    rss_30         = { cadence = 30, cpu = 256, memory = 512 }
    api_60         = { cadence = 60, cpu = 512, memory = 1024 }
    playwright_360 = { cadence = 360, cpu = 1024, memory = 2048 }
    arxiv_1440     = { cadence = 1440, cpu = 512, memory = 1024 }
  }
}

resource "aws_ecs_task_definition" "ingestion" {
  for_each = local.cadence_groups

  family                   = "${var.project}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.ecs_task.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "ingestion"
    image = each.key == "playwright_360" ? aws_ecr_repository.ingestion_playwright.repository_url : aws_ecr_repository.ingestion.repository_url
    command = [
      "python", "-m", "ingestion.main", "run",
      "--group", each.key,
    ]
    environment = [
      { name = "EG_ENV", value = "prod" },
      { name = "EG_S3_BUCKET", value = var.lakehouse_bucket },
      { name = "EG_SECRETS_ID", value = "${var.project}/credentials" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.project}"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = each.key
      }
    }
  }])
}

# EventBridge schedules per cadence group

resource "aws_cloudwatch_event_rule" "ingestion_schedule" {
  for_each = local.cadence_groups

  name                = "${var.project}-${each.key}"
  description         = "EG ingestion ${each.key} cadence"
  schedule_expression = each.value.cadence == 30 ? "rate(30 minutes)" : (
    each.value.cadence == 60 ? "rate(1 hour)" : (
      each.value.cadence == 360 ? "rate(6 hours)" : "rate(24 hours)"
    )
  )
}

resource "aws_cloudwatch_event_target" "ingestion_ecs" {
  for_each = local.cadence_groups

  rule      = aws_cloudwatch_event_rule.ingestion_schedule[each.key].name
  target_id = "ecs-${each.key}"
  arn       = aws_ecs_cluster.ingestion.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.ingestion[each.key].arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = var.subnet_ids
      security_groups  = var.security_group_ids
      assign_public_ip = false
    }
  }
}

resource "aws_iam_role" "eventbridge_ecs" {
  name = "${var.project}-eventbridge-ecs"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
    }]
  })
}

variable "subnet_ids" {
  type    = list(string)
  default = []
}

variable "security_group_ids" {
  type    = list(string)
  default = []
}

output "lakehouse_bucket" {
  value = aws_s3_bucket.lakehouse.id
}

output "ecr_ingestion_url" {
  value = aws_ecr_repository.ingestion.repository_url
}

output "ecr_playwright_url" {
  value = aws_ecr_repository.ingestion_playwright.repository_url
}
