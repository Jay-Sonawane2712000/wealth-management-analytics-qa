# Exploratory advisor/account AUM growth model.
#
# This script uses local synthetic wealth-management data to fit a simple
# regression model for account-level monthly AUM growth. It is an analysis
# artifact for reporting context, not a production forecasting model.

get_script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) > 0) {
    return(dirname(normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = FALSE)))
  }
  normalizePath(getwd(), winslash = "/", mustWork = FALSE)
}

project_root <- normalizePath(file.path(get_script_dir(), ".."), winslash = "/", mustWork = FALSE)
input_dir <- file.path(project_root, "data", "raw", "synthetic")
report_path <- file.path(project_root, "reports", "r_aum_growth_model_summary.md")
plot_dir <- file.path(project_root, "outputs", "r")
residual_plot_path <- file.path(plot_dir, "residuals_vs_fitted.png")
segment_plot_path <- file.path(plot_dir, "aum_growth_by_segment.png")

required_packages <- c("readr", "dplyr", "ggplot2", "broom")
missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing_packages) > 0) {
  message("Missing required R packages: ", paste(missing_packages, collapse = ", "))
  message("Install them with: install.packages(c(\"readr\", \"dplyr\", \"ggplot2\", \"broom\"))")
  quit(status = 1)
}

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(ggplot2)
  library(broom)
})

input_files <- c(
  advisors = file.path(input_dir, "synthetic_advisors.csv"),
  accounts = file.path(input_dir, "synthetic_accounts.csv"),
  performance = file.path(input_dir, "synthetic_monthly_performance.csv")
)

missing_files <- input_files[!file.exists(input_files)]
if (length(missing_files) > 0) {
  message("Synthetic input files were not found.")
  message("Please generate local synthetic data first:")
  message("python -m ingestion.generate_synthetic")
  message("Missing files:")
  message(paste(" -", missing_files, collapse = "\n"))
  quit(status = 1)
}

dir.create(dirname(report_path), recursive = TRUE, showWarnings = FALSE)
dir.create(plot_dir, recursive = TRUE, showWarnings = FALSE)

advisors <- readr::read_csv(input_files[["advisors"]], show_col_types = FALSE)
accounts <- readr::read_csv(input_files[["accounts"]], show_col_types = FALSE)
performance <- readr::read_csv(input_files[["performance"]], show_col_types = FALSE)

model_data <- performance %>%
  inner_join(
    accounts %>% select(account_id, client_segment, account_status),
    by = "account_id"
  ) %>%
  inner_join(
    advisors %>% select(advisor_id, advisor_tenure_years, primary_client_segment),
    by = "advisor_id"
  ) %>%
  mutate(
    beginning_aum = as.numeric(beginning_aum),
    ending_aum = as.numeric(ending_aum),
    fee_rate = as.numeric(fee_rate),
    advisor_tenure_years = as.numeric(advisor_tenure_years),
    aum_growth_rate = (ending_aum - beginning_aum) / beginning_aum,
    client_segment = as.factor(client_segment),
    primary_client_segment = as.factor(primary_client_segment)
  ) %>%
  filter(
    is.finite(aum_growth_rate),
    is.finite(advisor_tenure_years),
    is.finite(fee_rate),
    !is.na(client_segment),
    !is.na(primary_client_segment)
  )

if (nrow(model_data) < 10) {
  message("Not enough usable rows to fit the R AUM growth model.")
  message("Please regenerate synthetic data and try again.")
  quit(status = 1)
}

model_formula <- aum_growth_rate ~ advisor_tenure_years + fee_rate + client_segment + primary_client_segment
aum_growth_model <- lm(model_formula, data = model_data)

coefficient_summary <- broom::tidy(aum_growth_model)
confidence_intervals <- broom::tidy(aum_growth_model, conf.int = TRUE) %>%
  select(term, estimate, conf.low, conf.high, p.value)
model_glance <- broom::glance(aum_growth_model)
augmented <- broom::augment(aum_growth_model)

residual_summary <- data.frame(
  observation_count = nrow(model_data),
  r_squared = model_glance$r.squared,
  adjusted_r_squared = model_glance$adj.r.squared,
  residual_std_error = model_glance$sigma,
  residual_mean = mean(augmented$.resid),
  residual_sd = sd(augmented$.resid),
  max_abs_standardized_residual = max(abs(augmented$.std.resid), na.rm = TRUE),
  max_cooks_distance = max(augmented$.cooksd, na.rm = TRUE)
)

markdown_table <- function(df, digits = 5) {
  formatted <- df
  numeric_columns <- vapply(formatted, is.numeric, logical(1))
  formatted[numeric_columns] <- lapply(formatted[numeric_columns], round, digits = digits)
  header <- paste("|", paste(names(formatted), collapse = " | "), "|")
  separator <- paste("|", paste(rep("---", length(formatted)), collapse = " | "), "|")
  rows <- apply(formatted, 1, function(row) paste("|", paste(row, collapse = " | "), "|"))
  c(header, separator, rows)
}

client_segment_summary <- model_data %>%
  group_by(client_segment) %>%
  summarise(
    account_month_rows = n(),
    avg_aum_growth_rate = mean(aum_growth_rate),
    median_aum_growth_rate = median(aum_growth_rate),
    .groups = "drop"
  )

residual_plot <- ggplot(augmented, aes(x = .fitted, y = .resid)) +
  geom_point(alpha = 0.35, color = "#2F5D7C") +
  geom_hline(yintercept = 0, color = "#8C2D19", linewidth = 0.7) +
  labs(
    title = "Residuals vs Fitted Values",
    x = "Fitted AUM growth rate",
    y = "Residual"
  ) +
  theme_minimal()

segment_plot <- ggplot(model_data, aes(x = client_segment, y = aum_growth_rate)) +
  geom_boxplot(fill = "#D9EAF7", color = "#2F5D7C", outlier_alpha = 0.25) +
  labs(
    title = "Monthly AUM Growth by Client Segment",
    x = "Client segment",
    y = "AUM growth rate"
  ) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 20, hjust = 1))

ggsave(residual_plot_path, residual_plot, width = 7, height = 4.5, dpi = 150)
ggsave(segment_plot_path, segment_plot, width = 7, height = 4.5, dpi = 150)

report_lines <- c(
  "# R AUM Growth Model Summary",
  "",
  paste("Generated on:", as.character(Sys.Date())),
  "",
  "## Purpose",
  "",
  "This analysis uses R to explore account-level monthly AUM growth patterns in the synthetic wealth-management baseline. It supports the finance analytics story by showing how statistical analysis can sit beside the Python QA and reporting pipeline.",
  "",
  "This is not a production forecasting model. It is an exploratory reporting artifact that helps frame advisor, fee, and segment relationships before downstream stakeholder reporting.",
  "",
  "## Data Used",
  "",
  paste("- Advisors file:", input_files[["advisors"]]),
  paste("- Accounts file:", input_files[["accounts"]]),
  paste("- Monthly performance file:", input_files[["performance"]]),
  paste("- Joined account-month rows used:", format(nrow(model_data), big.mark = ",")),
  paste("- Distinct advisors:", format(dplyr::n_distinct(model_data$advisor_id), big.mark = ",")),
  paste("- Distinct accounts:", format(dplyr::n_distinct(model_data$account_id), big.mark = ",")),
  "",
  "## Model Formula",
  "",
  "`aum_growth_rate ~ advisor_tenure_years + fee_rate + client_segment + primary_client_segment`",
  "",
  "AUM growth rate is calculated as `(ending_aum - beginning_aum) / beginning_aum`.",
  "",
  "## Coefficient Summary",
  "",
  markdown_table(coefficient_summary),
  "",
  "## Confidence Intervals",
  "",
  markdown_table(confidence_intervals),
  "",
  "## Residual Diagnostics Summary",
  "",
  markdown_table(residual_summary),
  "",
  "Residual diagnostics plot:",
  "",
  "- `outputs/r/residuals_vs_fitted.png`",
  "",
  "## Client Segment Summary",
  "",
  markdown_table(client_segment_summary),
  "",
  "Client-segment plot:",
  "",
  "- `outputs/r/aum_growth_by_segment.png`",
  "",
  "## Key Takeaways",
  "",
  "- The model gives a concise way to inspect whether tenure, fee rate, and client segment are associated with monthly AUM growth in the generated baseline.",
  "- Coefficients should be interpreted directionally and cautiously because the data is synthetic.",
  "- Residual diagnostics help show whether the linear model is leaving visible structure unexplained.",
  "- This R artifact complements the main Python QA layer by adding a finance-analysis lens to the same reporting domain.",
  "",
  "## Limitations",
  "",
  "- The data is synthetic, so coefficients do not describe real adviser behavior or real client outcomes.",
  "- The model is exploratory and should not be presented as production machine learning or a deployable forecasting tool.",
  "- The formula is intentionally simple and does not account for market benchmarks, nested account/advisor effects, serial correlation, or branch-level structure.",
  "- Seeded-error QA remains the project's main technical depth; this model supports the analytics story without replacing the QA evaluation layer."
)

writeLines(report_lines, report_path)
message("R AUM growth model summary written to: ", report_path)
message("R plots written to: ", plot_dir)
