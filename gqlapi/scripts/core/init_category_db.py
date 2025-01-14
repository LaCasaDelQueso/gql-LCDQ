""" Script to initialize the category database.

This script is used to initialize the category database with the
restaurant, and supplier categories.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.core.init_category_db --help
    # python -m gqlapi.scripts.core.init_category_db --restaurant (init | save) --supplier (init | save)
"""
import asyncio
import argparse
import uuid

from gqlapi.domain.models.v2.core import Category, CoreUser
from gqlapi.domain.models.v2.utils import CategoryType
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup
from gqlapi.repository.core.category import CategoryRepository
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo


restaurant_category_list = [
    {"value": "africana", "label": "Africana"},
    {"value": "bebicas-alcoholicas", "label": "Bebicas Alcoholicas"},
    {"value": "argentina", "label": "Argentina"},
    {"value": "asiatica", "label": "Asiatica"},
    {"value": "panadería", "label": "Panadería"},
    {"value": "panadería-y-pastelería", "label": "Panadería y Pastelería"},
    {"value": "comida-de-bar", "label": "Comida de bar"},
    {"value": "barbacoa", "label": "Barbacoa"},
    {"value": "brasileña", "label": "Brasileña"},
    {"value": "desayuno-bruch", "label": "Desayuno Bruch"},
    {"value": "te-de-burbujas", "label": "Te de burbujas"},
    {"value": "hamburguesas", "label": "Hamburguesas"},
    {"value": "burritos", "label": "Burritos"},
    {"value": "cajún", "label": "Cajún"},
    {"value": "pastel", "label": "Pastel"},
    {"value": "caribeña", "label": "Caribeña"},
    {"value": "pollo", "label": "Pollo"},
    {"value": "chilena", "label": "Chilena"},
    {"value": "china", "label": "China"},
    {"value": "cafe-y-te", "label": "Cafe y Te"},
    {"value": "colombiana", "label": "Colombiana"},
    {"value": "crepas-o-crepería", "label": "Crepas o Crepería"},
    {"value": "postres", "label": "Postres"},
    {"value": "ecuatoriana", "label": "Ecuatoriana"},
    {"value": "egipcia", "label": "Egipcia"},
    {"value": "empanadas", "label": "Empanadas"},
    {"value": "europea", "label": "Europea"},
    {"value": "filipina", "label": "Filipina"},
    {"value": "pescado-frito-c/-papas", "label": "Pescado Frito C/ papas"},
    {"value": "pescado-y-mariscos", "label": "Pescado y Mariscos"},
    {"value": "francés", "label": "Francés"},
    {"value": "alemana", "label": "Alemana"},
    {"value": "gourmet", "label": "Gourmet"},
    {"value": "griega", "label": "Griega"},
    {"value": "guatemalteca", "label": "Guatemalteca"},
    {"value": "halal", "label": "Halal"},
    {"value": "hawaiana", "label": "Hawaiana"},
    {"value": "saludable", "label": "Saludable"},
    {"value": "helado-y-yogurt", "label": "Helado y Yogurt"},
    {"value": "india", "label": "India"},
    {"value": "indionesia", "label": "Indionesia"},
    {"value": "israelí", "label": "Israelí"},
    {"value": "italiana", "label": "Italiana"},
    {"value": "japonesa", "label": "Japonesa"},
    {"value": "ramen", "label": "Ramen"},
    {"value": "sushi", "label": "Sushi"},
    {"value": "jugos-y-licuados", "label": "Jugos y Licuados"},
    {"value": "kebab", "label": "Kebab"},
    {"value": "coreana", "label": "Coreana"},
    {"value": "kosher", "label": "Kosher"},
    {"value": "libanesa", "label": "Libanesa"},
    {"value": "malasia", "label": "Malasia"},
    {"value": "mediterránea", "label": "Mediterránea"},
    {"value": "mexicana", "label": "Mexicana"},
    {"value": "medio-oriente", "label": "Medio Oriente"},
    {"value": "australiana-moderna", "label": "Australiana moderna"},
    {"value": "marroquí", "label": "Marroquí"},
    {"value": "paquistaní", "label": "Paquistaní"},
    {"value": "peruana", "label": "Peruana"},
    {"value": "pizza", "label": "Pizza"},
    {"value": "poke", "label": "Poke"},
    {"value": "portuguesa", "label": "Portuguesa"},
    {"value": "rusa", "label": "Rusa"},
    {"value": "ensaladas/sandwiches", "label": "Ensaladas/sandwiches"},
    {"value": "mariscos", "label": "Mariscos"},
    {"value": "bocadillos", "label": "Bocadillos"},
    {"value": "sureña", "label": "Sureña"},
    {"value": "española", "label": "Española"},
    {"value": "carnes-a-la-parrilla", "label": "Carnes a la parrilla"},
    {"value": "tacos", "label": "Tacos"},
    {"value": "tex-mex", "label": "Tex-Mex"},
    {"value": "tailandesa", "label": "Tailandesa"},
    {"value": "turca", "label": "Turca"},
    {"value": "vegetariana-vegana", "label": "Vegetariana-Vegana"},
    {"value": "venezolana", "label": "Venezolana"},
    {"value": "vietnamita", "label": "Vietnamita"},
    {"value": "alitas", "label": "Alitas"},
    {"value": "otro", "label": "Otro"},
]

supplier_category_list = [
    {"value": "lacteos-y-huevos", "label": "Lácteos y Huevos"},
    {"value": "secos", "label": "Secos"},
    {"value": "carnes", "label": "Carnes"},
    {"value": "abarrotes", "label": "Abarrotes"},
    {"value": "frutas-y-verduras", "label": "Frutas y Verduras"},
    {"value": "pescados-y-maríscos", "label": "Pescados y Maríscos"},
    {"value": "bebidas", "label": "Bebidas"},
    {"value": "empaques", "label": "Empaques"},
    {"value": "panaderia-y-tortillería", "label": "Panadería y Tortillería"},
    {"value": "limpieza", "label": "Limpieza"},
    {"value": "utensilios-de-cocina", "label": "Utensilios de Cocina"},
    {"value": "equipo-de-cocina", "label": "Equipo de Cocina"},
    {"value": "otro", "label": "Otro"},
]


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Initialize the category database.")
    parser.add_argument(
        "--restaurant",
        help="Flag to initialize the restaurant category database.",
        choices=["init", "update"],
        default=None,
    )
    parser.add_argument(
        "--supplier",
        help="Flag to initialize the supplier category database.",
        choices=["init", "update"],
        default=None,
    )
    return parser.parse_args()


# init db routine
async def init_restaurant_category_db():
    """Initialize the restaurant category database."""
    _info = InjectedStrawberryInfo(db=SQLDatabase, mongo=None)
    await db_startup()
    categ_repo = CategoryRepository(info=_info)  # type: ignore
    core_repo = CoreUserRepository(info=_info)  # type: ignore
    # review if there are categories
    _id = await categ_repo.db.fetch_one(
        "SELECT id FROM category where lower(category_type) = 'restaurant' LIMIT 1"
    )
    if _id:
        print("Restaurant category database already initialized.")
        return
    # get admin user or create it
    try:
        tmp = await core_repo.get_by_email("admin")
        admin_user = tmp.id
        if not admin_user:
            raise Exception("Error getting admin user")
    except Exception:
        admin_user = await core_repo.new(
            CoreUser(
                id=uuid.uuid4(),
                email="admin",
                first_name="Alima",
                last_name="Bot",
                firebase_id="admin",
            )
        )
    # insert categories
    try:
        for cat in restaurant_category_list:
            await categ_repo.new(
                Category(
                    id=uuid.uuid4(),
                    name=cat["label"],
                    keywords=[cat["value"]],
                    category_type=CategoryType.RESTAURANT,
                    created_by=admin_user,
                )
            )
            print(f"Correctly inserted {cat['label']} category")
    except Exception as e:
        print("Error inserting categories: ", e)
    await db_shutdown()


# init db routine
async def init_supplier_category_db():
    """Initialize the supplier category database."""
    _info = InjectedStrawberryInfo(db=SQLDatabase, mongo=None)
    await db_startup()
    categ_repo = CategoryRepository(info=_info)  # type: ignore
    core_repo = CoreUserRepository(info=_info)  # type: ignore
    # review if there are categories
    _id = await categ_repo.db.fetch_one(
        "SELECT id FROM category where lower(category_type) = 'supplier' LIMIT 1"
    )
    if _id:
        print("Supplier category database already initialized.")
        return
    # get admin user or create it
    try:
        tmp = await core_repo.get_by_email("admin")
        admin_user = tmp.id
        if not admin_user:
            raise Exception("Error getting admin user")
    except Exception:
        admin_user = await core_repo.new(
            CoreUser(
                id=uuid.uuid4(),
                email="admin",
                first_name="Alima",
                last_name="Bot",
                firebase_id="admin",
            )
        )
    # insert categories
    try:
        for cat in supplier_category_list:
            await categ_repo.new(
                Category(
                    id=uuid.uuid4(),
                    name=cat["label"],
                    keywords=[cat["value"]],
                    category_type=CategoryType.SUPPLIER,
                    created_by=admin_user,
                )
            )
            print(f"Correctly inserted {cat['label']} category")
    except Exception as e:
        print("Error inserting categories: ", e)
    await db_shutdown()


async def main():
    args = parse_args()
    if args.restaurant:
        if args.restaurant == "init":
            await init_restaurant_category_db()
        elif args.restaurant == "update":
            print("Not implemented yet")
    if args.supplier:
        if args.supplier == "init":
            await init_supplier_category_db()
        elif args.supplier == "update":
            print("Not implemented yet")


if __name__ == "__main__":
    asyncio.run(main())
