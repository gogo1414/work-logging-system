output "lambda_function_arn" {
  description = "생성된 Lambda 함수 ARN"
  value       = aws_lambda_function.this.arn
}

output "api_endpoint" {
  description = "API Gateway 기본 호출 URL"
  value       = aws_apigatewayv2_api.this.api_endpoint
}
