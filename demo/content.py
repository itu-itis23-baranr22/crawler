"""Kitchen Notes, the demo site: every page, built from the recipes below.

The site is made up, though the dishes are real. It is built the same way every time, so a crawl
of it always finds the same thing. Some addresses are broken on purpose, so that a crawl meets one
of each outcome: see the end of build_site.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

ROOT = "/demo"
SITE_NAME = "Kitchen Notes"


@dataclass
class Block:
    heading: str = ""
    paragraphs: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)  # a bulleted list
    steps: List[str] = field(default_factory=list)  # a numbered list
    links: List[Tuple[str, str, str]] = field(default_factory=list)  # address, words, a note after the link


@dataclass
class Page:
    title: str
    gloss: str = ""
    lead: str = ""
    facts: str = ""
    trail: List[Tuple[str, str]] = field(default_factory=list)  # where the page sits, as (address, words)
    blocks: List[Block] = field(default_factory=list)
    status: int = 200
    noindex: bool = False
    canonical: Optional[str] = None


@dataclass
class Moved:
    to: str


@dataclass
class PlainText:
    text: str


Entry = Union[Page, Moved, PlainText]


def at(path: str) -> str:
    return ROOT + path


CATEGORIES = {
    "soups": ("Soups", "Çorbalar", "Soup starts many meals, and lentil soup is the one most cooks make without a recipe."),
    "breakfast": ("Breakfast", "Kahvaltı", "A table of small plates, with one hot egg dish cooked in the pan it is served in."),
    "mezes": ("Mezes", "Mezeler", "Small cold dishes to share, made ahead, and best with bread."),
    "mains": ("Mains", "Ana yemekler", "Stews, meatballs and stuffed vegetables for the middle of the table."),
    "vegetables": (
        "Olive oil dishes",
        "Zeytinyağlılar",
        "Vegetables cooked slowly in olive oil and served at room temperature, often the next day.",
    ),
    "pastry": ("Breads and pastry", "Hamur işleri", "Flatbreads, buns and layered pastry, from the bakery and the home oven."),
    "desserts": ("Desserts", "Tatlılar", "Milk puddings and semolina sweets, most of them made a day ahead."),
}

INGREDIENTS = {
    "red-lentils": ("Red lentils", "Split red lentils cook down in half an hour without soaking. They are the base of the everyday soups."),
    "bulgur": ("Bulgur", "Wheat that has been boiled, dried and cracked. Fine bulgur only needs soaking; coarse bulgur is cooked like rice."),
    "yogurt": (
        "Yogurt",
        "Plain whole-milk yogurt, used cold in dips and sauces, cooked in soups, and as a marinade. "
        "Strained yogurt is thick enough to spread.",
    ),
    "tomato-paste": (
        "Tomato and pepper paste",
        "Salça: tomatoes or red peppers cooked down and dried in the sun until dark and thick. "
        "A spoon of it fried in butter is how many dishes begin.",
    ),
    "pul-biber": ("Pul biber", "Flakes of dried red pepper, mild to medium hot and a little oily, sometimes sold as Aleppo pepper."),
    "aubergine": (
        "Aubergine",
        "The vegetable of summer: fried, stuffed, braised or charred over a flame. Peeling it in stripes helps it keep its shape.",
    ),
    "olive-oil": ("Olive oil", "Used generously, above all in the vegetable dishes that are cooked in it and named after it."),
    "dried-mint": ("Dried mint", "Stronger and sweeter than fresh mint. Rub it between your palms over the pot, or warm it in butter."),
    "pomegranate-molasses": (
        "Pomegranate molasses",
        "Nar ekşisi: pomegranate juice boiled down until thick and sour. It dresses salads and sharpens dips.",
    ),
    "white-cheese": ("White cheese", "Beyaz peynir, a brined cheese a little like feta, crumbled into pastries or eaten at breakfast."),
    "sucuk": ("Sucuk", "A dry, garlicky beef sausage seasoned with cumin and red pepper. It is sliced and fried, never eaten raw."),
    "semolina": ("Semolina", "Coarsely milled durum wheat, toasted for halva or baked into cakes soaked in syrup."),
    "walnuts": ("Walnuts", "Pounded into dips, scattered over puddings, and folded into pastries."),
    "grape-molasses": ("Grape molasses", "Pekmez: grape juice boiled down to a dark syrup. It browns simit, and is eaten with tahini."),
    "garlic": ("Garlic", "Crushed raw into yogurt, or sliced and cooked slowly with onions in the olive oil dishes."),
    "dill": ("Dill", "The herb of spring vegetables and broad beans, added at the end so it stays green."),
    "lemon": ("Lemon", "Squeezed over soups, salads and olive oil dishes just before eating."),
}

TECHNIQUES = {
    "pepper-butter": (
        "Red pepper butter",
        [
            "Melt butter until it foams, take it off the heat, and stir in pul biber. The butter turns red in seconds.",
            "Pour it over soups, yogurt and dumplings at the table. Heated too long, the pepper burns and turns bitter.",
        ],
    ),
    "tempering-yogurt": (
        "Keeping yogurt from splitting",
        [
            "Yogurt boiled on its own separates into curds and whey. Whisk it with an egg yolk and a spoon of flour first.",
            "Then whisk in a few ladles of the hot liquid before pouring it all back, and stir over low heat until it just simmers.",
        ],
    ),
    "charring-aubergines": (
        "Charring aubergines",
        [
            "Lay whole aubergines on a gas flame or under a very hot grill, and turn them until the skin is black and they collapse.",
            "Peel them while hot and drain the flesh in a sieve, so the purée isn't watery. The smoke is the flavour.",
        ],
    ),
    "olive-oil-braising": (
        "Cooking in olive oil",
        [
            "Zeytinyağlı dishes are vegetables cooked slowly in plenty of olive oil, with a little water, sugar and lemon.",
            "They cool in the pot and are served at room temperature, often the next day, when they taste better.",
        ],
    ),
    "rolling-yufka": (
        "Rolling dough thin",
        [
            "Use a long thin rolling pin, an oklava. Wrap the sheet around the pin and roll it back and forth to stretch it.",
            "Dust with flour or starch between turns. The sheet is ready when you can see the board through it.",
        ],
    ),
    "soaking-pulses": (
        "Soaking dried beans",
        [
            "Cover dried chickpeas and beans with plenty of cold water overnight, then drain and cook them in fresh water.",
            "Split red lentils need no soaking. Dried broad beans do better with a few hours.",
        ],
    ),
}


@dataclass
class Recipe:
    category: str
    slug: str
    name: str
    gloss: str
    serves: str
    time: str
    about: str
    ingredients: List[str]
    steps: List[str]
    uses: List[str] = field(default_factory=list)  # ingredient pages
    techniques: List[str] = field(default_factory=list)


RECIPES = [
    # ---------- Soups ----------
    Recipe(
        "soups", "mercimek-corbasi", "Mercimek çorbası", "Red lentil soup", "Serves 4", "40 minutes",
        "A smooth soup of red lentils, onion and carrot, finished with butter sizzled with red pepper and a squeeze of lemon.",
        ["250 g red lentils, rinsed", "1 onion, chopped", "1 carrot, chopped", "1 small potato, chopped",
         "1 tablespoon tomato paste", "2 tablespoons butter", "1.5 litres water or stock", "1 teaspoon ground cumin",
         "1 teaspoon pul biber", "Lemon wedges"],
        ["Soften the onion, carrot and potato in half the butter for 5 minutes.",
         "Stir in the tomato paste and cumin, then add the lentils and water.",
         "Simmer for 30 minutes, until the lentils fall apart, then blend until smooth and season.",
         "Melt the rest of the butter with the pul biber, spoon it over each bowl, and serve with lemon."],
        ["red-lentils", "tomato-paste", "pul-biber", "lemon"], ["pepper-butter"],
    ),
    Recipe(
        "soups", "ezogelin-corbasi", "Ezogelin çorbası", "Red lentil and bulgur soup", "Serves 4", "45 minutes",
        "A thicker, tangier cousin of lentil soup, with bulgur and rice for body and dried mint for its smell.",
        ["150 g red lentils", "2 tablespoons fine bulgur", "2 tablespoons rice", "1 onion, chopped", "1 tablespoon tomato paste",
         "1 teaspoon red pepper paste", "2 tablespoons butter", "1.5 litres water", "1 tablespoon dried mint", "1 teaspoon pul biber"],
        ["Soften the onion in the butter, then stir in both pastes.",
         "Add the lentils, bulgur, rice and water and simmer for 35 minutes, stirring now and then.",
         "Rub the mint between your palms over the pot, season, and serve without blending."],
        ["red-lentils", "bulgur", "tomato-paste", "dried-mint", "pul-biber"],
    ),
    Recipe(
        "soups", "yayla-corbasi", "Yayla çorbası", "Yogurt and rice soup with mint", "Serves 4", "35 minutes",
        "A pale, gently sour soup of yogurt and rice. The yogurt is tempered with egg and flour so it doesn't split as it heats.",
        ["500 g plain yogurt", "1 egg yolk", "1 tablespoon flour", "80 g rice", "1.2 litres water or chicken stock",
         "2 tablespoons butter", "1 tablespoon dried mint"],
        ["Simmer the rice in the water until soft, about 15 minutes.",
         "Whisk the yogurt, egg yolk and flour together, then whisk in two ladles of the hot liquid.",
         "Pour the yogurt into the pot and stir over low heat until it just simmers.",
         "Warm the mint in the butter for a few seconds and pour it over the soup."],
        ["yogurt", "dried-mint"], ["tempering-yogurt"],
    ),
    Recipe(
        "soups", "domates-corbasi", "Domates çorbası", "Tomato soup with grated cheese", "Serves 4", "30 minutes",
        "Fresh tomatoes cooked down with a little flour and milk, with grated kaşar cheese melting on top.",
        ["1 kg ripe tomatoes, grated", "1 tablespoon tomato paste", "2 tablespoons butter", "2 tablespoons flour",
         "750 ml water or stock", "200 ml milk", "Grated kaşar or another mild melting cheese"],
        ["Cook the flour in the butter for 2 minutes, then stir in the tomato paste.",
         "Add the tomatoes and water and simmer for 15 minutes.",
         "Stir in the milk, warm it through, and blend if you like it smooth.",
         "Serve with the cheese scattered on top."],
        ["tomato-paste"],
    ),
    Recipe(
        "soups", "tarhana-corbasi", "Tarhana çorbası", "Soup from dried tarhana", "Serves 4", "25 minutes",
        "Tarhana is a dried, crumbled mix of fermented yogurt, flour and vegetables, made in late summer for the winter. "
        "A few spoons make a sour, warming soup.",
        ["4 tablespoons tarhana", "1 tablespoon tomato paste", "2 tablespoons butter", "1.2 litres water", "1 teaspoon dried mint"],
        ["Soak the tarhana in a glass of cold water for 15 minutes.",
         "Melt the butter, stir in the tomato paste, then add the tarhana and the rest of the water.",
         "Simmer for 10 minutes, stirring so it doesn't catch, and finish with the mint."],
        ["yogurt", "tomato-paste", "dried-mint"],
    ),
    # ---------- Breakfast ----------
    Recipe(
        "breakfast", "menemen", "Menemen", "Eggs with tomatoes and peppers", "Serves 2", "20 minutes",
        "Soft eggs stirred through tomatoes and green peppers cooked down in olive oil or butter. "
        "Whether it has onion in it is an argument with no winner.",
        ["2 long green peppers, sliced", "3 ripe tomatoes, grated", "4 eggs", "2 tablespoons olive oil or butter", "Pul biber and salt"],
        ["Cook the peppers in the oil until soft, about 5 minutes.",
         "Add the tomatoes and cook until most of the juice has gone.",
         "Crack in the eggs and stir gently until just set. Serve from the pan, with bread."],
        ["olive-oil", "pul-biber"],
    ),
    Recipe(
        "breakfast", "cilbir", "Çılbır", "Poached eggs on garlic yogurt", "Serves 2", "15 minutes",
        "Poached eggs on cool garlicky yogurt, with hot red pepper butter poured over the top.",
        ["300 g thick yogurt, at room temperature", "1 small garlic clove, crushed", "4 eggs", "2 tablespoons butter",
         "1 teaspoon pul biber", "A splash of vinegar"],
        ["Stir the garlic and a pinch of salt into the yogurt and spread it on two plates.",
         "Poach the eggs in simmering water with the vinegar for 3 minutes and set them on the yogurt.",
         "Sizzle the pul biber in the butter and spoon it over the eggs."],
        ["yogurt", "garlic", "pul-biber"], ["pepper-butter"],
    ),
    Recipe(
        "breakfast", "sucuklu-yumurta", "Sucuklu yumurta", "Eggs fried with sucuk", "Serves 2", "10 minutes",
        "Slices of sucuk, a dry spiced sausage, fried until their fat runs, with eggs cracked into the pan.",
        ["100 g sucuk, thinly sliced", "4 eggs", "1 teaspoon butter"],
        ["Fry the sucuk in the butter until it curls and gives up its fat.",
         "Crack in the eggs and cook until the whites set. Serve in the pan."],
        ["sucuk"],
    ),
    Recipe(
        "breakfast", "gozleme", "Gözleme", "Griddle flatbread with spinach and cheese", "Serves 4", "1 hour",
        "Thin sheets of dough folded around a filling and cooked on a hot griddle, brushed with butter.",
        ["400 g flour", "250 ml warm water", "1 teaspoon salt", "200 g spinach, chopped", "200 g white cheese, crumbled",
         "1 onion, finely chopped", "Melted butter"],
        ["Knead the flour, water and salt into a soft dough and rest it for 30 minutes.",
         "Divide it into 4 and roll each piece out as thin as you can.",
         "Spread the filling over half, fold, and seal the edges.",
         "Cook on a dry griddle for 3 minutes a side, brushing with butter."],
        ["white-cheese"], ["rolling-yufka"],
    ),
    Recipe(
        "breakfast", "kuymak", "Kuymak", "Cornmeal and cheese from the Black Sea", "Serves 2", "20 minutes",
        "Cornmeal cooked in plenty of butter, then stirred with a stretchy cheese until it pulls into strings. "
        "Eaten from the pan, with bread.",
        ["3 tablespoons butter", "3 tablespoons cornmeal", "300 ml water", "150 g stretchy cheese such as kolot or mozzarella"],
        ["Melt the butter and toast the cornmeal in it for 2 minutes.",
         "Add the water and stir until it thickens.",
         "Add the cheese and keep stirring over low heat until the butter separates and the cheese stretches."],
    ),
    # ---------- Mezes ----------
    Recipe(
        "mezes", "haydari", "Haydari", "Thick yogurt with garlic and herbs", "Serves 4", "10 minutes, plus draining",
        "Strained yogurt beaten with garlic, dill and mint until thick enough to hold a spoon upright.",
        ["500 g strained yogurt", "1 garlic clove, crushed", "1 small bunch dill, chopped", "1 tablespoon dried mint",
         "2 tablespoons olive oil"],
        ["If your yogurt is runny, drain it in a cloth overnight.",
         "Beat in the garlic, the herbs and a pinch of salt.",
         "Spread it on a plate and pour the oil over."],
        ["yogurt", "garlic", "dill", "olive-oil"],
    ),
    Recipe(
        "mezes", "acili-ezme", "Acılı ezme", "Chopped hot tomato and pepper salad", "Serves 4", "20 minutes",
        "Tomato, pepper, onion and parsley chopped so finely they almost become a paste, dressed with pomegranate molasses.",
        ["2 tomatoes, seeded", "1 red pepper", "1 hot green pepper", "1 small onion", "1 small bunch parsley",
         "1 tablespoon pomegranate molasses", "1 tablespoon olive oil", "1 teaspoon pul biber"],
        ["Chop the vegetables and parsley very finely, by hand, until they start to come together.",
         "Stir in the molasses, oil and pul biber, season, and leave for 10 minutes before serving."],
        ["pomegranate-molasses", "olive-oil", "pul-biber"],
    ),
    Recipe(
        "mezes", "kisir", "Kısır", "Fine bulgur salad", "Serves 6", "30 minutes",
        "Fine bulgur softened with hot water and tomato paste, then mixed with herbs, spring onions and a sour dressing.",
        ["250 g fine bulgur", "250 ml hot water", "1 tablespoon tomato paste", "1 tablespoon red pepper paste",
         "4 spring onions, sliced", "1 bunch parsley, chopped", "A handful of mint, chopped", "Juice of 1 lemon",
         "2 tablespoons pomegranate molasses", "4 tablespoons olive oil"],
        ["Pour the hot water over the bulgur, cover, and leave it for 15 minutes.",
         "Knead in both pastes with your hands until the bulgur is evenly red.",
         "Mix in everything else, season, and serve with lettuce leaves."],
        ["bulgur", "tomato-paste", "pomegranate-molasses", "lemon", "olive-oil"],
    ),
    Recipe(
        "mezes", "patlican-salatasi", "Patlıcan salatası", "Smoky aubergine salad", "Serves 4", "40 minutes",
        "Aubergines charred over a flame until they collapse, then chopped with garlic, lemon and olive oil.",
        ["3 aubergines", "1 garlic clove, crushed", "Juice of half a lemon", "3 tablespoons olive oil", "Chopped parsley"],
        ["Char the aubergines over a gas flame or under a hot grill until black all over and soft.",
         "Peel them, drain the flesh in a sieve, and chop it with a knife.",
         "Mix in the garlic, lemon and oil, and season."],
        ["aubergine", "garlic", "lemon", "olive-oil"], ["charring-aubergines"],
    ),
    Recipe(
        "mezes", "muhammara", "Muhammara", "Red pepper and walnut dip", "Serves 6", "25 minutes",
        "Roasted red peppers pounded with walnuts, breadcrumbs and pepper paste, sweet and sour from pomegranate molasses.",
        ["2 red peppers, roasted and peeled", "100 g walnuts", "40 g breadcrumbs", "1 tablespoon red pepper paste",
         "1 tablespoon pomegranate molasses", "1 garlic clove", "1 teaspoon ground cumin", "3 tablespoons olive oil"],
        ["Pound or pulse the walnuts until coarse.",
         "Add everything else and work it into a thick paste that still has some texture.",
         "Season, and finish with more oil."],
        ["walnuts", "pomegranate-molasses", "garlic", "olive-oil"],
    ),
    Recipe(
        "mezes", "fava", "Fava", "Broad bean purée with dill", "Serves 6", "1 hour, plus setting",
        "Dried split broad beans cooked with onion until they fall apart, beaten with olive oil, set in a dish, and sliced.",
        ["250 g dried split broad beans", "1 onion, chopped", "100 ml olive oil", "1 teaspoon sugar", "Chopped dill and lemon"],
        ["Soak the beans for a few hours, then cook them with the onion in just enough water to cover until very soft.",
         "Beat in the oil and sugar until smooth, season, and pour into a dish.",
         "Leave it to set, then turn it out and slice it. Serve with dill, lemon and more oil."],
        ["olive-oil", "dill", "lemon"], ["soaking-pulses"],
    ),
    # ---------- Mains ----------
    Recipe(
        "mains", "karniyarik", "Karnıyarık", "Aubergines split and filled with meat", "Serves 4", "1 hour 15 minutes",
        "Whole aubergines fried until soft, split open, and filled with minced meat, onion and tomato, then baked.",
        ["4 aubergines", "300 g minced beef or lamb", "1 onion, chopped", "2 garlic cloves", "2 tomatoes, chopped",
         "2 long green peppers", "1 tablespoon tomato paste", "Oil for frying"],
        ["Peel the aubergines in stripes, fry them whole until soft, and drain them.",
         "Brown the meat with the onion and garlic, then add the tomatoes and cook until thick.",
         "Split each aubergine lengthways, open it like a boat, and fill it.",
         "Top with pepper, pour over the tomato paste loosened with water, and bake at 180 °C for 30 minutes."],
        ["aubergine", "garlic", "tomato-paste"],
    ),
    Recipe(
        "mains", "izmir-kofte", "İzmir köfte", "Baked meatballs with potatoes", "Serves 4", "1 hour",
        "Meatballs and potato wedges baked in a tomato sauce with green peppers.",
        ["500 g minced beef", "1 onion, grated", "1 slice stale bread, soaked", "1 egg", "1 teaspoon ground cumin",
         "3 potatoes, cut into wedges", "3 long green peppers", "2 tablespoons tomato paste", "300 ml hot water"],
        ["Knead the meat with the onion, bread, egg, cumin and salt, and shape it into fingers.",
         "Brown the meatballs, and fry the potato wedges briefly.",
         "Lay them in a dish with the peppers, pour over the paste mixed with the water, and bake at 200 °C for 30 minutes."],
        ["tomato-paste"],
    ),
    Recipe(
        "mains", "tavuk-sis", "Tavuk şiş", "Marinated chicken skewers", "Serves 4", "30 minutes, plus marinating",
        "Chicken thighs marinated in yogurt and red pepper paste, threaded on skewers and grilled hard.",
        ["800 g boneless chicken thighs, in chunks", "3 tablespoons yogurt", "1 tablespoon red pepper paste",
         "2 garlic cloves, crushed", "2 tablespoons olive oil", "1 teaspoon pul biber"],
        ["Mix the yogurt, pepper paste, garlic, oil and pul biber, and coat the chicken. Leave it for at least 2 hours.",
         "Thread it on skewers and grill over high heat, turning, for 12 to 15 minutes."],
        ["yogurt", "garlic", "pul-biber"],
    ),
    Recipe(
        "mains", "etli-nohut", "Etli nohut", "Chickpea and lamb stew", "Serves 4", "2 hours, plus soaking",
        "Chickpeas and small pieces of lamb stewed with tomato paste until soft, eaten over rice.",
        ["250 g dried chickpeas, soaked overnight", "300 g lamb, in small cubes", "1 onion, chopped",
         "1 tablespoon tomato paste", "1 tablespoon butter"],
        ["Boil the soaked chickpeas for 45 minutes and drain them.",
         "Brown the lamb in the butter, add the onion, then the tomato paste.",
         "Add the chickpeas and water to cover, and simmer for an hour, until both are tender."],
        ["tomato-paste"], ["soaking-pulses"],
    ),
    Recipe(
        "mains", "manti", "Mantı", "Tiny dumplings with garlic yogurt", "Serves 4", "1 hour 30 minutes",
        "Small squares of dough pinched around a little spiced meat, boiled, and served under garlic yogurt and red pepper butter.",
        ["300 g flour", "1 egg", "120 ml water", "200 g minced beef", "1 small onion, grated",
         "400 g yogurt with 1 crushed garlic clove", "2 tablespoons butter", "1 teaspoon pul biber", "Dried mint"],
        ["Knead the flour, egg, water and salt into a firm dough and rest it.",
         "Roll it thin, cut it into 2 cm squares, and put a pea of meat and onion on each.",
         "Pinch the corners together, boil for 10 minutes, and drain.",
         "Serve under the garlic yogurt, with the pepper butter and mint on top."],
        ["yogurt", "garlic", "pul-biber", "dried-mint"], ["rolling-yufka", "pepper-butter"],
    ),
    Recipe(
        "mains", "hunkar-begendi", "Hünkâr beğendi", "Lamb stew on smoky aubergine purée", "Serves 4", "2 hours",
        "A tomato and lamb stew served on a smooth purée of charred aubergine, milk and cheese.",
        ["500 g lamb, in cubes", "1 onion, chopped", "2 tomatoes, chopped", "1 tablespoon tomato paste", "4 aubergines",
         "2 tablespoons butter", "2 tablespoons flour", "300 ml milk", "50 g grated kaşar or parmesan"],
        ["Brown the lamb, add the onion, tomatoes and paste, cover with water, and simmer for 1 hour 30 minutes.",
         "Char, peel and mash the aubergines.",
         "Cook the flour in the butter, whisk in the milk, then beat in the aubergine and cheese.",
         "Spoon the purée onto plates and the stew into the middle."],
        ["aubergine", "tomato-paste"], ["charring-aubergines"],
    ),
    # ---------- Olive oil dishes ----------
    Recipe(
        "vegetables", "imam-bayildi", "İmam bayıldı", "Aubergines stuffed with onion and tomato", "Serves 4", "1 hour 15 minutes",
        "Aubergines softened in olive oil and filled with onion, garlic and tomato, then cooked slowly and served cool. "
        "The name means the imam fainted.",
        ["4 small aubergines", "3 onions, sliced", "6 garlic cloves, sliced", "3 tomatoes, chopped", "1 bunch parsley, chopped",
         "150 ml olive oil", "1 teaspoon sugar"],
        ["Peel the aubergines in stripes, salt them for 20 minutes, rinse, and fry them whole in some of the oil until soft.",
         "Cook the onions and garlic slowly in more oil until soft, then add the tomatoes, sugar and parsley.",
         "Split the aubergines, fill them, add the rest of the oil and a little water, and cook covered on low heat for 30 minutes.",
         "Let them cool in the pan, and serve at room temperature."],
        ["aubergine", "olive-oil", "garlic"], ["olive-oil-braising"],
    ),
    Recipe(
        "vegetables", "taze-fasulye", "Zeytinyağlı taze fasulye", "Green beans braised in olive oil", "Serves 4", "1 hour",
        "Flat green beans cooked slowly with onion and tomato in olive oil until soft.",
        ["750 g flat green beans, trimmed", "1 onion, chopped", "3 tomatoes, grated", "100 ml olive oil", "1 teaspoon sugar"],
        ["Soften the onion in the oil.",
         "Add the beans, tomatoes, sugar, salt and half a glass of water.",
         "Cover and cook on low heat for 45 minutes, until the beans are soft. Serve cool."],
        ["olive-oil"], ["olive-oil-braising"],
    ),
    Recipe(
        "vegetables", "yaprak-sarma", "Zeytinyağlı yaprak sarma", "Vine leaves rolled around spiced rice", "Serves 6", "2 hours",
        "Vine leaves rolled tightly around rice with onion, pine nuts, currants and spices, then simmered under a plate.",
        ["40 vine leaves in brine, rinsed", "250 g rice", "2 onions, finely chopped", "2 tablespoons pine nuts",
         "2 tablespoons currants", "1 teaspoon allspice", "1 teaspoon cinnamon", "1 tablespoon dried mint", "150 ml olive oil",
         "1 lemon, sliced"],
        ["Cook the onions and pine nuts in half the oil, add the rice, spices, currants, mint and a glass of water, "
         "and cook until it is absorbed.",
         "Roll a teaspoon of filling in each leaf, as thin as a finger.",
         "Pack them tightly in a pan, top with the lemon, the rest of the oil and water to cover, and weigh them down with a plate.",
         "Simmer for 45 minutes and leave them to cool in the pan."],
        ["olive-oil", "dried-mint", "lemon"], ["olive-oil-braising"],
    ),
    Recipe(
        "vegetables", "enginar", "Zeytinyağlı enginar", "Artichokes with peas and dill", "Serves 4", "50 minutes",
        "Artichoke hearts cooked with carrots, peas and baby onions in olive oil and lemon, finished with dill. A spring dish.",
        ["6 artichoke hearts, kept in lemon water", "1 carrot, diced", "100 g peas", "8 baby onions", "100 ml olive oil",
         "Juice of 1 lemon", "1 teaspoon sugar", "Chopped dill"],
        ["Lay the artichokes in a wide pan, cup side up, and fill them with the carrot, peas and onions.",
         "Pour over the oil, lemon, sugar, salt and a glass of water.",
         "Cover with paper and cook gently for 35 minutes. Let them cool, and serve with dill."],
        ["olive-oil", "lemon", "dill"], ["olive-oil-braising"],
    ),
    Recipe(
        "vegetables", "pirasa", "Zeytinyağlı pırasa", "Leeks with carrot and rice", "Serves 4", "45 minutes",
        "Leeks cut in chunks and cooked with carrot and a little rice in olive oil and lemon.",
        ["4 leeks, in 3 cm pieces", "1 carrot, sliced", "2 tablespoons rice", "80 ml olive oil", "Juice of half a lemon",
         "1 teaspoon sugar"],
        ["Cook the carrot in the oil for 5 minutes, then add the leeks.",
         "Add the rice, sugar, lemon, salt and a glass of water.",
         "Cover and cook for 30 minutes. Serve cool, with more lemon."],
        ["olive-oil", "lemon"], ["olive-oil-braising"],
    ),
    Recipe(
        "vegetables", "barbunya-pilaki", "Barbunya pilaki", "Borlotti beans in olive oil", "Serves 4", "1 hour 30 minutes, plus soaking",
        "Borlotti beans cooked with carrot, potato, garlic and tomato in plenty of olive oil, served cold with parsley.",
        ["250 g dried borlotti beans, soaked overnight", "1 onion, chopped", "4 garlic cloves", "1 carrot, diced",
         "1 potato, diced", "1 tablespoon tomato paste", "100 ml olive oil"],
        ["Boil the beans for 40 minutes and drain them.",
         "Soften the onion and garlic in the oil, add the paste, then the carrot and potato.",
         "Add the beans and water to cover, and simmer for 30 minutes. Let it cool, and serve with parsley and lemon."],
        ["olive-oil", "garlic", "tomato-paste"], ["soaking-pulses", "olive-oil-braising"],
    ),
    # ---------- Breads and pastry ----------
    Recipe(
        "pastry", "su-boregi", "Su böreği", "Layered pastry with cheese", "Serves 8", "1 hour 30 minutes",
        "Sheets of thin dough boiled one by one, then layered with butter, white cheese and parsley and baked until golden.",
        ["500 g flour", "4 eggs", "Water as needed", "300 g white cheese, crumbled", "1 bunch parsley, chopped", "150 g melted butter"],
        ["Knead the flour, eggs and a little water into a firm dough, divide it into 8, and rest it.",
         "Roll each piece as wide as the tray, boil it for a minute, and cool it in cold water.",
         "Layer the sheets in a buttered tray, with butter on each and the cheese and parsley in the middle.",
         "Bake at 200 °C for 35 minutes, until golden."],
        ["white-cheese"], ["rolling-yufka"],
    ),
    Recipe(
        "pastry", "kiymali-pide", "Kıymalı pide", "Boat-shaped flatbread with minced meat", "Serves 4", "2 hours",
        "Yeasted dough stretched into long boats, topped with spiced minced meat, tomato and pepper, and baked very hot.",
        ["500 g flour", "1 teaspoon dried yeast", "300 ml warm water", "300 g minced beef", "1 onion, finely chopped",
         "1 tomato, finely chopped", "1 green pepper, finely chopped", "1 tablespoon tomato paste", "Butter for brushing"],
        ["Make a soft dough with the flour, yeast, water and salt, and leave it to rise for an hour.",
         "Mix the meat with the vegetables, the paste and seasoning.",
         "Stretch each piece of dough into a long oval, spread the topping, and fold the edges in.",
         "Bake at the highest heat for 8 to 10 minutes and brush with butter."],
        ["tomato-paste"],
    ),
    Recipe(
        "pastry", "simit", "Simit", "Sesame bread rings", "Makes 8", "2 hours",
        "Twisted rings of dough dipped in grape molasses and coated thickly in sesame, sold from carts all over Istanbul.",
        ["500 g flour", "1 teaspoon dried yeast", "300 ml warm water", "100 ml grape molasses mixed with 200 ml water",
         "200 g sesame seeds, toasted"],
        ["Make a firm dough, let it rise for an hour, and divide it into 8.",
         "Roll each piece into two ropes, twist them together, and close them into a ring.",
         "Dip the rings in the molasses water, then press them into the sesame.",
         "Bake at 220 °C for 15 to 20 minutes."],
        ["grape-molasses"],
    ),
    Recipe(
        "pastry", "pogaca", "Poğaça", "Soft cheese buns", "Makes 12", "1 hour 30 minutes",
        "Soft, rich buns with a little white cheese and parsley inside, brushed with egg yolk. A bakery breakfast.",
        ["500 g flour", "1 teaspoon dried yeast", "200 ml warm milk", "100 ml oil", "100 g yogurt", "1 egg, separated",
         "150 g white cheese mixed with parsley"],
        ["Make a soft dough with the flour, yeast, milk, oil, yogurt and egg white, and let it rise.",
         "Divide it into 12, fill each piece with cheese, and fold it into a half-moon.",
         "Brush with the yolk and bake at 180 °C for 25 minutes."],
        ["yogurt", "white-cheese"],
    ),
    Recipe(
        "pastry", "lahmacun", "Lahmacun", "Thin flatbread with spiced meat", "Makes 8", "1 hour 30 minutes",
        "Very thin rounds of dough spread with minced meat, pepper, tomato and parsley, baked in minutes, "
        "and rolled up with lemon and more parsley.",
        ["400 g flour", "1 teaspoon dried yeast", "250 ml warm water", "250 g minced lamb or beef",
         "1 onion, 1 tomato and 1 red pepper, all very finely chopped", "1 tablespoon red pepper paste", "1 teaspoon pul biber",
         "Parsley and lemon"],
        ["Make a dough, let it rise, and divide it into 8 balls.",
         "Mix the meat, vegetables, paste and pul biber into a paste you can spread.",
         "Roll each ball very thin, spread it thinly with the topping, and bake at the highest heat for 5 to 7 minutes.",
         "Squeeze over lemon, add parsley, and roll it up."],
        ["pul-biber", "lemon"],
    ),
    # ---------- Desserts ----------
    Recipe(
        "desserts", "firin-sutlac", "Fırın sütlaç", "Baked rice pudding", "Serves 6", "1 hour",
        "Rice cooked in milk until creamy, poured into bowls, and browned under a hot grill.",
        ["80 g rice", "1 litre milk", "150 g sugar", "2 tablespoons rice flour or cornflour", "1 teaspoon vanilla"],
        ["Cook the rice in a glass of water until it is absorbed.",
         "Add the milk and sugar and simmer for 20 minutes.",
         "Thicken it with the rice flour mixed with a little cold milk, and add the vanilla.",
         "Pour into ovenproof bowls, stand them in a tray of water, and brown them under the grill. Chill."],
    ),
    Recipe(
        "desserts", "irmik-helvasi", "İrmik helvası", "Semolina halva", "Serves 6", "30 minutes",
        "Semolina and pine nuts toasted slowly in butter, then soaked with sweet hot milk. "
        "It is made for guests, and shared with neighbours after a funeral.",
        ["250 g coarse semolina", "125 g butter", "2 tablespoons pine nuts", "500 ml milk", "200 g sugar"],
        ["Toast the semolina and pine nuts in the butter over low heat, stirring, for 20 minutes, until golden.",
         "Heat the milk with the sugar and pour it in carefully, as it will spit.",
         "Stir until it is absorbed, cover, and leave it for 10 minutes before serving."],
        ["semolina"],
    ),
    Recipe(
        "desserts", "asure", "Aşure", "Pudding of grains, beans and fruit", "Serves 12", "3 hours, plus soaking",
        "A thick pudding of wheat, chickpeas, beans, dried fruit and nuts. Families make a big pot and share it with neighbours.",
        ["200 g whole wheat, soaked overnight", "50 g chickpeas, soaked and cooked", "50 g white beans, soaked and cooked",
         "100 g dried apricots, chopped", "100 g dried figs, chopped", "50 g raisins", "250 g sugar",
         "Walnuts, pomegranate seeds and cinnamon"],
        ["Simmer the wheat in plenty of water for 2 hours, until it bursts.",
         "Add the chickpeas, beans, dried fruit and sugar, and simmer for 30 minutes more.",
         "Pour it into bowls, let it set, and top with walnuts, pomegranate and cinnamon."],
        ["walnuts"], ["soaking-pulses"],
    ),
    Recipe(
        "desserts", "kazandibi", "Kazandibi", "Milk pudding with a caramelised base", "Serves 8", "1 hour",
        "A milk pudding cooked on a sugared tray until the bottom caramelises, then cut and rolled so the brown side shows.",
        ["1 litre milk", "200 g sugar", "4 tablespoons rice flour", "2 tablespoons cornflour", "1 teaspoon vanilla",
         "Butter and sugar for the tray"],
        ["Cook the milk, sugar and flours, whisking, until thick, then add the vanilla.",
         "Butter a metal tray, sprinkle it with sugar, and heat it on the stove until the sugar browns.",
         "Pour in the pudding and keep it on the heat for a few minutes more, until the bottom caramelises.",
         "Chill, cut it into strips, and roll each one with the brown side out."],
    ),
    Recipe(
        "desserts", "revani", "Revani", "Semolina sponge in syrup", "Serves 12", "1 hour, plus soaking",
        "A light sponge made with semolina and yogurt, soaked in lemon syrup while it is hot.",
        ["4 eggs", "150 g sugar", "200 g yogurt", "150 g semolina", "100 g flour", "2 teaspoons baking powder",
         "For the syrup: 400 g sugar, 500 ml water and a slice of lemon"],
        ["Boil the syrup for 10 minutes and let it cool.",
         "Whisk the eggs and sugar until pale, then fold in the yogurt, semolina, flour and baking powder.",
         "Bake at 180 °C for 30 minutes, then pour the cool syrup over the hot cake.",
         "Leave it for a few hours before cutting."],
        ["semolina", "yogurt", "lemon"],
    ),
]

RECIPE_AT = {recipe.slug: recipe for recipe in RECIPES}

# A recipe taken down. The soups page still links to it, as pages tend to.
REMOVED = ("soups", "balik-corbasi", "Balık çorbası", "Fish soup")

POSTS = {
    "a-week-of-soups": (
        "A week of soups",
        "January",
        [
            "Every winter we make a different soup each night for a week, starting with the plainest: "
            "lentil soup on Monday, with the pepper butter that makes it.",
            "By Thursday the soups turn sour. Tarhana, from the batch dried in the summer, and yayla with its yogurt and mint.",
            "Fish soup used to close the week. It is off the site while we fix the recipe.",
        ],
        [("soups", "mercimek-corbasi"), ("soups", "tarhana-corbasi"), ("soups", "yayla-corbasi"), ("soups", "balik-corbasi")],
    ),
    "olive-oil-dishes-wait": (
        "Why olive oil dishes wait a day",
        "March",
        [
            "Vegetables cooked in olive oil are never served hot. They cool in the pot, "
            "and the oil, lemon and juices settle into each other overnight.",
            "Make them a day ahead, and take them out of the fridge an hour before eating.",
        ],
        [("vegetables", "imam-bayildi"), ("vegetables", "taze-fasulye"), ("vegetables", "yaprak-sarma")],
    ),
    "the-breakfast-table": (
        "The breakfast table",
        "April",
        [
            "A weekend breakfast takes the whole morning: white cheese, olives, tomatoes and cucumbers, honey with clotted cream, "
            "jam, simit from the corner, and one small glass of tea after another.",
            "Then one hot dish, cooked in the pan it is served in. Menemen, sucuk with eggs, or on the Black Sea, kuymak.",
        ],
        # Simit's old address, from before the bakery section was renamed. It still works, by redirect.
        [("breakfast", "menemen"), ("breakfast", "sucuklu-yumurta"), ("breakfast", "kuymak"), ("pastries", "simit")],
    ),
    "spring-market": (
        "At the spring market",
        "May",
        [
            "Artichokes arrive already trimmed, floating in lemon water, next to fresh broad beans and bunches of dill "
            "as long as your arm.",
            "Most of it goes into olive oil and comes out the next day.",
        ],
        [("vegetables", "enginar"), ("mezes", "fava"), ("vegetables", "pirasa")],
    ),
    "bread-for-the-neighbours": (
        "Bread for the neighbours",
        "June",
        [
            "On baking days the oven stays hot all afternoon. Pide first, then poğaça, and the last of the heat for a tray of su böreği.",
            "Whatever doesn't fit on the table goes next door.",
        ],
        [("pastry", "kiymali-pide"), ("pastry", "pogaca"), ("pastry", "su-boregi")],
    ),
}

DRAFTS = {
    "lahana-sarma": ("Lahana sarması", "Cabbage leaves rolled around rice and meat. Not tested yet."),
    "new-year-menu": ("A New Year menu", "Notes for a long winter dinner. Not written yet."),
}


def _recipe_link(recipe: Recipe) -> Tuple[str, str, str]:
    return at(f"/{recipe.category}/{recipe.slug}"), recipe.name, recipe.gloss


def _recipe_page(recipe: Recipe, *, canonical: Optional[str] = None) -> Page:
    name, _, _ = CATEGORIES[recipe.category]
    blocks = [Block("Ingredients", items=recipe.ingredients), Block("Method", steps=recipe.steps)]
    more = [(at(f"/ingredients/{slug}"), INGREDIENTS[slug][0], "") for slug in recipe.uses]
    more += [(at(f"/techniques/{slug}"), TECHNIQUES[slug][0], "technique") for slug in recipe.techniques]
    if more:
        blocks.append(Block("More about", links=more))
    return Page(
        title=recipe.name,
        gloss=recipe.gloss,
        lead=recipe.about,
        facts=f"{recipe.serves} · {recipe.time}",
        trail=[(at(f"/{recipe.category}/"), name)],
        blocks=blocks,
        canonical=canonical,
    )


def build_site() -> Dict[str, Entry]:
    """Every address on the site, after /demo, and what it serves."""
    site: Dict[str, Entry] = {}

    sections = [(at(f"/{slug}/"), name, intro) for slug, (name, _, intro) in CATEGORIES.items()]
    site["/"] = Page(
        title=SITE_NAME,
        lead="Home cooking from Turkey, written down as we make it.",
        blocks=[
            Block("Recipes", links=sections),
            Block(
                "Also here",
                links=[
                    (at("/journal/"), "Journal", "notes from the kitchen through the year"),
                    (at("/about"), "About this site", "and where to find ingredients and techniques"),
                    (at("/members/"), "Members' recipes", ""),
                    (at("/shopping-list"), "This week's shopping list", ""),
                ],
            ),
        ],
    )

    for slug, (name, turkish, intro) in CATEGORIES.items():
        links = [_recipe_link(recipe) for recipe in RECIPES if recipe.category == slug]
        if slug == REMOVED[0]:
            links.append((at(f"/{REMOVED[0]}/{REMOVED[1]}"), REMOVED[2], REMOVED[3]))
        site[f"/{slug}/"] = Page(title=name, gloss=turkish, lead=intro, blocks=[Block(links=links)])

    for recipe in RECIPES:
        site[f"/{recipe.category}/{recipe.slug}"] = _recipe_page(recipe)

    site["/ingredients/"] = Page(
        title="Ingredients",
        lead="The things that turn up in recipe after recipe.",
        blocks=[Block(links=[(at(f"/ingredients/{slug}"), name, "") for slug, (name, _) in INGREDIENTS.items()])],
    )
    for slug, (name, about) in INGREDIENTS.items():
        uses = [_recipe_link(recipe) for recipe in RECIPES if slug in recipe.uses]
        site[f"/ingredients/{slug}"] = Page(
            title=name,
            lead=about,
            trail=[(at("/ingredients/"), "Ingredients")],
            blocks=[Block("Used in", links=uses)],
        )

    site["/techniques/"] = Page(
        title="Techniques",
        lead="A few ways of working that the recipes take for granted.",
        blocks=[Block(links=[(at(f"/techniques/{slug}"), name, "") for slug, (name, _) in TECHNIQUES.items()])],
    )
    for slug, (name, paragraphs) in TECHNIQUES.items():
        uses = [_recipe_link(recipe) for recipe in RECIPES if slug in recipe.techniques]
        site[f"/techniques/{slug}"] = Page(
            title=name,
            trail=[(at("/techniques/"), "Techniques")],
            blocks=[Block(paragraphs=paragraphs), Block("Used in", links=uses)],
        )

    journal = Page(
        title="Journal",
        lead="Notes from the kitchen through the year.",
        blocks=[
            Block(links=[(at(f"/journal/{slug}"), title, month) for slug, (title, month, _, _) in POSTS.items()]),
            Block("Not finished", links=[(at("/journal/notes-to-self"), "Notes to self", "")]),
            Block("Coming soon", links=[(at(f"/drafts/{slug}"), title, "") for slug, (title, _) in DRAFTS.items()]),
            Block(links=[(at("/journal/archive"), "Archive", "every post so far")]),
        ],
    )
    site["/journal/"] = journal
    for slug, (title, month, paragraphs, mentions) in POSTS.items():
        links = []
        for category, recipe_slug in mentions:
            recipe = RECIPE_AT.get(recipe_slug)
            if recipe is None:
                links.append((at(f"/{category}/{recipe_slug}"), REMOVED[2], REMOVED[3]))
            else:
                links.append((at(f"/{category}/{recipe_slug}"), recipe.name, recipe.gloss))
        site[f"/journal/{slug}"] = Page(
            title=title,
            facts=month,
            trail=[(at("/journal/"), "Journal")],
            blocks=[Block(paragraphs=paragraphs), Block("Recipes in this post", links=links)],
        )

    site["/about"] = Page(
        title="About this site",
        blocks=[
            Block(
                paragraphs=[
                    "Kitchen Notes is made up. Crawler serves it at /demo/ so a crawl can be tried without leaving this computer. "
                    "The dishes are real, written down briefly.",
                    "Some of its addresses are broken on purpose, so a crawl meets one of each kind of outcome: a removed recipe, "
                    "a members-only page, an old address that redirects, drafts that robots.txt keeps out, a post marked noindex, "
                    "a printable copy of a recipe, an archive that repeats the journal, and a shopping list that isn't a web page.",
                ]
            ),
            Block(
                "Browse",
                links=[
                    (at("/ingredients/"), "Ingredients", "and the recipes that use them"),
                    (at("/techniques/"), "Techniques", "the recipes take for granted"),
                ],
            ),
        ],
    )

    # ---------- Broken on purpose: one of each outcome a crawl can meet ----------
    first = RECIPES[0]
    original = at(f"/{first.category}/{first.slug}")
    page = _recipe_page(first, canonical=original)
    page.blocks.insert(0, Block(paragraphs=["Printable version."]))
    site[f"/{first.category}/{first.slug}/print"] = page  # names the recipe as its canonical page
    site[f"/{first.category}/{first.slug}"].blocks.append(Block(links=[(original + "/print", "Printable version", "")]))
    site["/journal/archive"] = journal  # the same page under a second address
    site["/journal/notes-to-self"] = Page(
        title="Notes to self",
        trail=[(at("/journal/"), "Journal")],
        blocks=[Block(paragraphs=["Not ready. Try revani with less syrup, and kısır with more mint."])],
        noindex=True,
    )
    for slug, (title, note) in DRAFTS.items():
        site[f"/drafts/{slug}"] = Page(title=title, blocks=[Block(paragraphs=[note])])
    site["/pastries/simit"] = Moved(at("/pastry/simit"))
    site["/members/"] = Page(
        title="Members only",
        blocks=[Block(paragraphs=["Sign in to see members' recipes."])],
        status=403,
    )
    site["/shopping-list"] = PlainText(
        "Shopping list\n\nred lentils\nfine bulgur\naubergines x 6\nflat green beans\nyogurt, 1 kg\nwhite cheese\nlemons\ndill\n"
    )
    return site


PAGES = build_site()

# Addresses on the site that are disallowed in robots.txt.
ROBOTS_DISALLOW = [at("/drafts/")]
