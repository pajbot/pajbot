build: proto
proto:
	@python -m grpc_tools.protoc -I. pajbot/protos/bot.proto --python_out=. --pyi_out=. --grpc_python_out=.
