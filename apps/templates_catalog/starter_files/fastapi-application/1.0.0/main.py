from fastapi import FastAPI


app = FastAPI(title='AtlasCloud starter')


@app.get('/')
def read_root():
    return {'message': 'Your FastAPI application is running.'}
