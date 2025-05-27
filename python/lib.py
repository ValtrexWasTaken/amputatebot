"""
Library for functions
"""
def format_big_number(number):
    """

    :param number: original integer
    :return: formated string (e.g. 25650 => 25 650)
    """
    split: list = str(number).split(".")
    price_round: str = ""

    i = 0
    for char in split[0][::-1]:
        i = i + 1
        if i == 4:
            i = 0
            price_round += " "
        price_round += char

    try:
        return price_round[::-1] + "." + split[1]
    except IndexError:
        return price_round[::-1]


def seconds_convert(total_seconds):
    """

    :param total_seconds: total seconds
    :return: days hours minutes seconds
    """
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days} days")
    if hours:
        parts.append(f"{hours} hours")
    if minutes:
        parts.append(f"{minutes} minutes")
    if seconds or not parts:
        parts.append(f"{seconds} seconds")

    return ' '.join(parts)
