terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "daily_log_api" {
  source          = "../../modules/aws_api_lambda"
  docker_image_uri = var.docker_image_uri

  environment_variables = {
    NOTION_DB1_ID = var.notion_db1_id
    NOTION_DB2_ID = var.notion_db2_id
    NOTION_DB3_ID = var.notion_db3_id
  }

  ssm_parameters = {
    NOTION_API_KEY = {
      name            = var.ssm_parameter_notion_api_key
      with_decryption = true
    }
    API_AUTH_TOKEN = {
      name            = var.ssm_parameter_api_auth_token
      with_decryption = true
    }
  }
}
