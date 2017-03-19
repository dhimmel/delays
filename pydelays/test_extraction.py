import os

from .eutilities import pubmed_esummary
from .xml_to_dates import extract_articles_from_esummaries


directory = os.path.dirname(os.path.abspath(__file__))

pubmed_ids = [
    '27094199',  # Circ Cardiovasc Genet
    '26158728',  # PLoS Comput Biol
    '25648772',  # PeerJ
    '21736753',  # BioData Min
    '25915600',  # Nature Genet
    '20081222',  # Bioinformatics
]

esummary_path = os.path.join(directory, 'data', 'esummary.xml')


def test_esummary():
    """
    Run to recreate data/esummary.xml
    """
    with open(esummary_path, 'wt') as write_file:
        pubmed_esummary(pubmed_ids, write_file)


def test_extract_articles():
    n_articles = len(pubmed_ids)
    articles = extract_articles_from_esummaries(esummary_path, n_articles)
    assert len(articles) == n_articles
