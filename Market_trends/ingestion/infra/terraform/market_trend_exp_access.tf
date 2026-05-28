# Apply with AWS credentials that can modify bucket policy on market-trend-exp2:
#   terraform apply -target=aws_s3_bucket_policy.market_trend_exp

variable "market_trend_bucket" {
  type    = string
  default = "market-trend-exp2"
}

variable "ingestion_iam_user_arn" {
  type        = string
  description = "IAM user or role ARN used for bronze ingestion (NOT RAG-Client unless you choose it)"
  # Set via -var or terraform.tfvars — run: aws sts get-caller-identity --profile YOUR_PROFILE
}

variable "databricks_uc_role_arn" {
  type        = string
  description = "IAM role ARN used by Databricks UC storage credential (fill after creating in Databricks UI)"
  default     = ""
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "market_trend_exp_bucket" {
  statement {
    sid    = "AllowIngestionUser"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [var.ingestion_iam_user_arn]
    }
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.market_trend_bucket}"]
  }

  statement {
    sid    = "AllowIngestionUserObjects"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [var.ingestion_iam_user_arn]
    }
    actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.market_trend_bucket}/bronze/*"]
  }

  dynamic "statement" {
    for_each = var.databricks_uc_role_arn != "" ? [1] : []
    content {
      sid    = "AllowDatabricksUC"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = [var.databricks_uc_role_arn]
      }
      actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
      resources = ["arn:aws:s3:::${var.market_trend_bucket}"]
    }
  }

  dynamic "statement" {
    for_each = var.databricks_uc_role_arn != "" ? [1] : []
    content {
      sid    = "AllowDatabricksUCObjects"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = [var.databricks_uc_role_arn]
      }
      actions = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
      resources = ["arn:aws:s3:::${var.market_trend_bucket}/bronze/*"]
    }
  }
}

resource "aws_s3_bucket_policy" "market_trend_exp" {
  bucket = var.market_trend_bucket
  policy = data.aws_iam_policy_document.market_trend_exp_bucket.json
}

output "market_trend_bucket_policy_applied" {
  value = var.market_trend_bucket
}
