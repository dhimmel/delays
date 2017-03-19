import datetime
import mimetypes
import importlib
import logging
import itertools
import locale
import collections

import tqdm
import pandas
from lxml import etree

# Ensure datetime.datetime.strptime
locale.setlocale(locale.LC_ALL, 'en_US.utf8')

encoding_to_module = {
    'gzip': 'gzip',
    'bzip2': 'bz2',
    'xz': 'lzma',
}


def iterparse(path):
    """
    First yield the ElementTree root, then yield elements from an XML file.
    """
    # Automatically detect compression
    type_, encoding = mimetypes.guess_type(path)
    if encoding is None:
        opener = open
    else:
        module = encoding_to_module[encoding]
        opener = importlib.import_module(module).open

    # Open file and yield from the element tree
    with opener(path, 'rb') as read_file:
        context = etree.iterparse(read_file, events=('start', 'end'))
        yield next(context)[1]
        yield from (elem for event, elem in context if event == 'end')


def parse_date_text(text):
    """
    Parse an `eSummaryResult/DocSum/Item[@Name='History']/Item[@Type='Date']`
    element.
    The time on the date is discarded. A `datetime.date` object is returned
    """
    return datetime.datetime.strptime(text, '%Y/%m/%d %H:%M').date()


def parse_pubdate_text(text):
    """
    Parse the text contained by the following elements:

    `eSummaryResult/DocSum/Item[@Name='PubDate' @Type='Date']`
    `eSummaryResult/DocSum/Item[@Name='EPubDate' @Type='Date']`

    See https://www.nlm.nih.gov/bsd/licensee/elements_article_source.html
    A `datetime.date` object is returned or `None` if the date is incomplete
    or corrupted.
    """
    try:
        return datetime.datetime.strptime(text, '%Y %b %d').date()
    except ValueError:
        return None


def parse_esummary_history(docsum):
    """
    docsum is an xml Element.
    """
    # Extract all historical dates
    date_pairs = list()
    seen = set()
    for item in docsum.findall("Item[@Name='History']/Item[@Type='Date']"):
        name = item.get('Name')
        try:
            date_ = parse_date_text(item.text)
        except ValueError as e:
            id_ = int(docsum.findtext('Id'))
            msg = (f'article {id_}; name: {name}; '
                   f'date: {item.text}; error: {e}')
            logging.warning(msg)
            continue

        date_pair = name, date_
        if date_pair in seen:
            continue
        seen.add(date_pair)
        date_pairs.append(date_pair)
    date_pairs.sort(key=lambda x: x[0])
    history = dict()
    for name, group in itertools.groupby(date_pairs, key=lambda x: x[0]):
        for i, (name, date_) in enumerate(group):
            history[f'{name}_{i}'] = date_
    return history


def parse_esummary(elem):
    """
    Extract pubmed, journal, and date information from an eSummaryResult/DocSum
    """
    article = collections.OrderedDict()
    article['pubmed_id'] = int(elem.findtext('Id'))
    article['journal_nlm_id'] = elem.findtext("Item[@Name='NlmUniqueID']")
    for key, name in ('pub', 'PubDate'), ('epub', 'EPubDate'):
        xpath = f"Item[@Name='{name}'][@Type='Date']"
        text = elem.findtext(xpath)
        try:
            article[key] = parse_pubdate_text(text)
        except ValueError as e:
            msg = (f'article {article["pubmed_id"]}; name: {key}; '
                   f'date: {text}; error: {e}')
            logging.info(msg)
            continue
    history = parse_esummary_history(elem)
    article.update(history)
    return article


def extract_articles_from_esummaries(path, n_articles=None, tqdm=tqdm.tqdm):
    """
    Extract a list of articles (dictionaries with date information) from a
    an eSummaryResult XML file. Specify `n_articles` to enable a progress bar.
    """
    if n_articles is not None:
        progress_bar = tqdm(total=n_articles, unit='articles')

    parser = iterparse(path)
    root = next(parser)
    articles = list()
    for elem in parser:
        if elem.tag != 'DocSum':
            continue
        article = parse_esummary(elem)
        articles.append(article)
        if n_articles is not None:
            progress_bar.update(1)
        root.clear()  # Reset element to free memory

    if n_articles is not None:
        progress_bar.close()
    return articles


def articles_to_dataframe(articles):
    """
    Convert a list of articles created by `extract_articles_from_esummaries`
    into a pandas.DataFrame.
    """
    article_df = pandas.DataFrame(articles)
    article_df = article_df.sort_values(by='pubmed_id')
    article_df['published'] = article_df[['epub', 'pub']].min(axis='columns')
    return article_df
