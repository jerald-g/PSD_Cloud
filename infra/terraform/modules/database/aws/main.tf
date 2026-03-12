variable "identifier"     { type = string }
variable "instance_class" { type = string }
variable "storage_gb"     { type = number }
variable "db_name"        { type = string }
variable "username"       { type = string; sensitive = true }
variable "password"       { type = string; sensitive = true }
variable "tags"           { type = map(string) }

resource "aws_db_instance" "postgres" {
  identifier             = var.identifier
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.instance_class
  allocated_storage      = var.storage_gb
  storage_encrypted      = true
  db_name                = var.db_name
  username               = var.username
  password               = var.password
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.identifier}-final"
  backup_retention_period = 7
  deletion_protection    = true
  publicly_accessible    = false

  tags = var.tags
}

output "endpoint" { value = aws_db_instance.postgres.endpoint }
output "db_name"  { value = aws_db_instance.postgres.db_name }
