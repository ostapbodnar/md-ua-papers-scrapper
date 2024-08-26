def generate_year_pairs(start_year: int, end_year: int):
    """
    Generate year-by-year pairs for the provided range.

    :param start_year: The start year (inclusive).
    :param end_year: The end year (inclusive).
    :return: A list of tuples representing year pairs.
    """
    return [(year, year + 1) for year in range(start_year, end_year)]


if __name__ == "__main__":
    start_year = 2010
    end_year = 2020
    year_pairs = generate_year_pairs(start_year, end_year)
    print(year_pairs)
