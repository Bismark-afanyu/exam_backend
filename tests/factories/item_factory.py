import factory

from app.schemas.item import ItemCreate


class ItemCreateFactory(factory.Factory):
    class Meta:
        model = ItemCreate

    title = factory.Faker("word")
    description = factory.Faker("sentence")
