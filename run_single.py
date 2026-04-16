import asyncio
from localstock.db.database import get_engine, get_session_factory
from localstock.services.pipeline import Pipeline

async def main():
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        pipeline = Pipeline(session)
        result = await pipeline.run_single("HPG")
        print(f"Mã: {result['symbol']}")
        print(f"Trạng thái: {result['status']}")
        print(f"Giá: {result.get('prices', 0)} dòng")
        print(f"BCTC: {result.get('financials', 0)} báo cáo")
        print(f"Công ty: {result.get('company', False)}")
        print(f"Sự kiện: {result.get('events', 0)}")
        if result['errors']:
            print(f"Lỗi: {result['errors']}")
    await engine.dispose()

asyncio.run(main())