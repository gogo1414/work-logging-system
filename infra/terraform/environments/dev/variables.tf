variable "aws_region" {
  type        = string
  default     = "ap-northeast-2"
  description = "AWS 리전"
}

variable "docker_image_uri" {
  type        = string
  description = "ECR에 업로드된 도커 이미지 URI"
}

variable "notion_db1_id" {
  type        = string
  description = "Daily Work Logs 데이터베이스 ID"
}

variable "notion_db2_id" {
  type        = string
  description = "Weekly Achievements 데이터베이스 ID"
}

variable "notion_db3_id" {
  type        = string
  description = "Monthly Highlights 데이터베이스 ID"
}

variable "ssm_parameter_notion_api_key" {
  type        = string
  description = "Notion API 키를 보관한 SSM Parameter 이름"
}

variable "ssm_parameter_api_auth_token" {
  type        = string
  description = "API_AUTH_TOKEN을 보관한 SSM Parameter 이름"
}
