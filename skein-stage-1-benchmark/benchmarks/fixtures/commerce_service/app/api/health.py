def health_check():
    return {"status": "ok"}

def readiness_check():
    return health_check()
