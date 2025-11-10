bucket         = "replace-with-your-terraform-state-bucket"
key            = "work-logging-system/dev/terraform.tfstate"
region         = "ap-northeast-2"
dynamodb_table = "replace-with-your-terraform-lock-table"
encrypt        = true
