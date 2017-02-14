library(dplyr)

scopus_types = list(scopus_id = readr::col_character())

metric_df = 'https://github.com/dhimmel/journalmetrics/raw/34c000d4a00adf02b25a3b62a7d5e5e437091c1a/data/metrics.tsv.gz' %>%
  readr::read_tsv(col_types = scopus_types) %>%
  dplyr::filter(metric == 'SJR', year == 2014) %>%
  dplyr::mutate(sjr_2014 = value, sjr_2014_log10 = log10(value)) %>%
  dplyr::select(-year, -metric)

journal_df = 'https://github.com/dhimmel/journalmetrics/raw/34c000d4a00adf02b25a3b62a7d5e5e437091c1a/data/pubmed-map.tsv' %>%
  readr::read_tsv(col_types = scopus_types) %>%
  dplyr::inner_join(
    'https://github.com/dhimmel/delays/raw/2d05dbaf2d8eaf50c35533261ba4c29b70c350a8/data/journal-summaries.tsv' %>%
      readr::read_tsv()) %>%
  dplyr::filter(delay_type == 'Acceptance') %>%
  dplyr::filter(n_articles >= 100) %>%
  dplyr::inner_join(
    'https://github.com/dhimmel/journalmetrics/raw/34c000d4a00adf02b25a3b62a7d5e5e437091c1a/data/title-top-levels.tsv' %>%
      readr::read_tsv(col_types = scopus_types)) %>%
  dplyr::inner_join(
    'https://github.com/dhimmel/journalmetrics/raw/34c000d4a00adf02b25a3b62a7d5e5e437091c1a/data/title-attributes.tsv' %>%
      readr::read_tsv(col_types = scopus_types)) %>%
  dplyr::inner_join(metric_df) %>%
  dplyr::mutate(median_delay_int = round(median_delay)) %>%
  dplyr::mutate(n_articles_log10 = log10(n_articles))

head(journal_df)

ggplot2::qplot(x = sjr_2014_log10, data = journal_df)


#cv_lasso = mpath::cv.glmregNB(formula=median_delay_int ~ n_unique_delays + n_articles, data=journal_df, link='identity', alpha=1, n.cores=10)
broom::tidy(cv_lasso)


start_values = c('(Intercept)' = 100, n_articles_log10 = 0, n_unique_years = 0, top_level_subject = 100)

dummies = paste0('top_level_subject', unique(journal_df$top_level_subject))
start = rep(100, length(dummies))
names(start) <- dummies
start = c(start, n_articles_log10 = 0, n_unique_years = 0)

model = glm(median_delay ~ top_level_subject + main_publisher + n_articles_log10 + sjr_2014_log10 + open_access - 1,
            data = journal_df, family = Gamma(link = 'identity'), start = rep(1, 531))
broom::tidy(model)



