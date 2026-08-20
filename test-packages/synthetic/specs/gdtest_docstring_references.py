"""
gdtest_docstring_references — bibliography citations in NumPy-style docstrings.

Dimensions: L21
Focus: Two functions cite academic papers with `[@citekey]` markers resolved
       against a project bibliography.
"""

SPEC = {
    "name": "gdtest_docstring_references",
    "description": "NumPy-style docstrings with `[@citekey]` bibliography citations",
    "dimensions": ["L21"],
    "pyproject_toml": {
        "project": {
            "name": "gdtest-docstring-references",
            "version": "0.1.0",
            "description": "Test References section rendering",
        },
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
    },
    "config": {
        "parser": "numpy",
        "bibliography": "docs/references.bib",
    },
    "files": {
        "gdtest_docstring_references/__init__.py": '''\
            """Package with References sections in docstrings."""

            __version__ = "0.1.0"
            __all__ = ["quicksort", "binary_search"]


            def quicksort(arr: list) -> list:
                """
                Sort a list using the quicksort algorithm.

                Implements the classic quicksort algorithm with Lomuto
                partition scheme. Returns a new sorted list without
                modifying the original.

                Parameters
                ----------
                arr
                    A list of comparable elements to sort.

                Returns
                -------
                list
                    A new list containing the same elements in sorted order.

                Notes
                -----
                The average-case time complexity is O(n log n), but the
                worst case is O(n^2) when the pivot selection is poor
                (e.g., already sorted input with first-element pivot).

                This implementation uses the last element as the pivot
                and creates new lists for the partitions, so it is not
                in-place.

                The partition scheme follows Hoare [@hoare1961], and the
                complexity analysis follows Cormen [@cormen2009].

                Examples
                --------
                >>> quicksort([3, 1, 4, 1, 5, 9])
                [1, 1, 3, 4, 5, 9]

                >>> quicksort([])
                []
                """
                if len(arr) <= 1:
                    return list(arr)

                pivot = arr[-1]
                left = [x for x in arr[:-1] if x <= pivot]
                right = [x for x in arr[:-1] if x > pivot]
                return quicksort(left) + [pivot] + quicksort(right)


            def binary_search(arr: list, target: int) -> int:
                """
                Search for a target value in a sorted list.

                Uses the binary search algorithm to find the index of
                ``target`` in the sorted list ``arr``. Returns -1 if
                the target is not found.

                Parameters
                ----------
                arr
                    A sorted list of integers to search.
                target
                    The integer value to search for.

                Returns
                -------
                int
                    The index of ``target`` in ``arr``, or -1 if not found.

                Notes
                -----
                The input list must be sorted in ascending order. If the
                list is not sorted, the result is undefined.

                The time complexity is O(log n) and the space complexity
                is O(1).

                The algorithm and its analysis follow Knuth [@knuth1998].

                Examples
                --------
                >>> binary_search([1, 3, 5, 7, 9], 5)
                2

                >>> binary_search([1, 3, 5, 7, 9], 4)
                -1
                """
                low, high = 0, len(arr) - 1

                while low <= high:
                    mid = (low + high) // 2
                    if arr[mid] == target:
                        return mid
                    elif arr[mid] < target:
                        low = mid + 1
                    else:
                        high = mid - 1

                return -1
        ''',
        # Keep the bibliography in `docs/`, outside the build tree. The
        # `bibliography:` setting points to this source file, which Great Docs
        # copies into the build directory.
        "docs/references.bib": """\
            @article{hoare1961,
              title = {Algorithm 64: Quicksort},
              author = {Hoare, C. A. R.},
              year = {1961},
              journal = {Communications of the ACM},
              volume = {4},
              number = {7},
              pages = {321},
            }

            @book{cormen2009,
              title = {Introduction to Algorithms},
              author = {Cormen, Thomas H.},
              year = {2009},
              publisher = {MIT Press},
              edition = {3rd},
            }

            @book{knuth1998,
              title = {The Art of Computer Programming, Volume 3},
              author = {Knuth, Donald E.},
              year = {1998},
              publisher = {Addison-Wesley},
              edition = {2nd},
            }
        """,
        "README.md": """\
            # gdtest-docstring-references

            A synthetic package whose NumPy-style docstrings cite academic
            papers with `[@citekey]` markers and a project bibliography.
        """,
    },
    "expected": {
        "detected_name": "gdtest-docstring-references",
        "detected_module": "gdtest_docstring_references",
        "detected_parser": "numpy",
        "export_names": ["binary_search", "quicksort"],
        "num_exports": 2,
        "section_titles": ["Functions"],
        "has_user_guide": False,
        "coverage_exclude": ["nodoc", "bigcl", "ug", "supp", "hdg"],
    },
}
