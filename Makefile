install:
	@pip install -r requirements.txt

run:
	@uvicorn main:app

hot:
	@uvicorn main:app --reload