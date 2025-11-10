output "api_endpoint" {
  description = "배포된 HTTP API 엔드포인트"
  value       = module.daily_log_api.api_endpoint
}

output "lambda_function_arn" {
  description = "Lambda 함수 ARN"
  value       = module.daily_log_api.lambda_function_arn
}
