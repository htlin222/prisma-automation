# Seed Labels for ML Screening

This directory contains seed label files used to train the machine learning models in the PRISMA automation screening system. Seed labels are manually classified examples that provide the initial training data for the active learning system.

## File Format

Seed label files should be in CSV format with the following columns:

1. `entry_id`: The unique identifier of the article from the BibTeX file
2. `label`: Binary classification (1 for include, 0 for exclude)
3. `reason`: Text explanation for the classification decision

Example:
```csv
entry_id,label,reason
pubmed_12345678,1,Relevant randomized controlled trial
pubmed_87654321,0,Animal study not meeting inclusion criteria
```

## Creating Seed Labels

### Step 1: Identify Article IDs

First, you need to identify the article IDs from your BibTeX results file. You can extract these IDs using the following command:

```bash
head -n 50 output/your_results.bib | grep "@article" | cut -d'{' -f2 | cut -d',' -f1
```

This will show the first few article IDs from your BibTeX file.

### Step 2: Create the Seed Labels File

Create a new CSV file in this directory with a descriptive name (e.g., `pubmed_seed_labels.csv`). Add at least 3-5 articles with a mix of both positive (include) and negative (exclude) examples.

**Important**: The ML model requires both positive and negative examples to train properly. Make sure to include at least one article of each class.

### Step 3: Provide Detailed Reasons

For each article, provide a detailed reason for your classification decision. This helps with:
- Documentation of your screening criteria
- Understanding the model's training data
- Future reference when reviewing screening results

## Using Seed Labels

To use your seed labels file with the ML screening system, specify the path when running the screening script:

```bash
python src/python/ml_screening.py \
  --input-file output/your_results.bib \
  --output-dir output/screening \
  --seed-file search_terms/seed_labels/your_seed_labels.csv
```

Or use the test script:

```bash
python test_ml_screening.py  # Edit the script to point to your seed labels file
```

## Active Learning

The ML screening system uses active learning to improve over time. After the initial screening, it will identify the most uncertain articles and save them to `active_learning_samples.csv` in the output directory.

To improve the model:

1. Review these uncertain articles manually
2. Add them to your seed labels file with appropriate classifications
3. Run the screening again with the updated seed labels

This iterative process will improve the model's accuracy with minimal manual labeling effort.

## Tips for Effective Seed Labels

1. **Quality over quantity**: A few well-chosen examples are better than many poor ones
2. **Balance classes**: Include a similar number of positive and negative examples
3. **Cover edge cases**: Include borderline examples that are difficult to classify
4. **Use domain expertise**: Apply your subject matter knowledge when classifying
5. **Be consistent**: Follow the same criteria for all classifications

## Default Files

- `seed_labels.csv`: General-purpose seed labels for demonstration
- `pubmed_test_labels.csv`: Example seed labels for PubMed results

You can create additional seed label files for different databases or research questions as needed.
