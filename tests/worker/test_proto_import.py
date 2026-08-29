def test_proto_importable():
    from brew_worker.gen import worker_pb2, worker_pb2_grpc

    assert worker_pb2.DESCRIPTOR
    assert worker_pb2_grpc.WorkerServicer
