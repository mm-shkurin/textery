.PHONY: test fmt validate

test: fmt validate

fmt:
	terraform fmt -check -recursive

validate:
	terraform init -backend=false
	terraform validate
