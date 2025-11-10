variable "lambda_function_name" {
  type        = string
  default     = "work-logging-api"
  description = "배포할 Lambda 함수 이름"
}

variable "docker_image_uri" {
  type        = string
  description = "ECR에 업로드된 컨테이너 이미지 URI"
}

variable "environment_variables" {
  type        = map(string)
  default     = {}
  description = "Lambda에 주입할 일반 환경 변수"
}

variable "ssm_parameters" {
  type = map(object({
    name            = string
    with_decryption = optional(bool, true)
  }))
  default     = {}
  description = "SecureString SSM 파라미터 목록 (환경 변수로 주입)"
}
