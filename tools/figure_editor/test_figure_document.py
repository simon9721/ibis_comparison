from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tools.figure_editor.figure_document import FigureRecipe, recipe_for_csv, render_recipe


class FigureDocumentTest(unittest.TestCase):
    def test_recipe_round_trip_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "wave.csv"
            with data.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time_ns", "reference", "candidate"])
                writer.writeheader()
                for index in range(10):
                    writer.writerow(
                        {
                            "time_ns": index * 0.1,
                            "reference": index,
                            "candidate": index * 1.05,
                        }
                    )
            recipe = recipe_for_csv(data)
            recipe.figure.title = "Test"
            recipe.series[0].color = "#111111"
            recipe_path = root / "figure.json"
            recipe.save(recipe_path)
            loaded = FigureRecipe.load(recipe_path)
            self.assertEqual(loaded.x_column, "time_ns")
            self.assertEqual(loaded.figure.title, "Test")
            output = render_recipe(loaded, root / "figure.png")
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()

