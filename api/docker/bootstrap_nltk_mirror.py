"""Prepare NLTK downloader with a mirror-friendly package index (build-time only)."""

from __future__ import annotations

import os
import pathlib
import urllib.request

import nltk.downloader as nltk_downloader
from nltk.downloader import Downloader


def main() -> None:
    nltk_data = os.environ["NLTK_DATA"]
    pathlib.Path(nltk_data).mkdir(parents=True, exist_ok=True)

    index_url = os.environ.get(
        "NLTK_INDEX_XML_URL",
        "https://cdn.jsdelivr.net/gh/nltk/nltk_data@gh-pages/index.xml",
    )
    old_prefix = os.environ.get(
        "NLTK_PACKAGE_URL_PREFIX",
        "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/",
    )
    new_prefix = os.environ.get(
        "NLTK_PACKAGE_URL_REPLACEMENT",
        "https://cdn.jsdelivr.net/gh/nltk/nltk_data@gh-pages/",
    )

    with urllib.request.urlopen(index_url) as response:
        xml_text = response.read().decode()
    rewritten = xml_text.replace(old_prefix, new_prefix)
    index_path = pathlib.Path(nltk_data) / "_mirror_index.xml"
    index_path.write_text(rewritten)

    downloader = Downloader(
        server_index_url=index_path.resolve().as_uri(),
        download_dir=nltk_data,
    )
    nltk_downloader._downloader = downloader
    nltk_downloader.download = downloader.download

    import nltk

    nltk.download = downloader.download

    from unstructured.nlp.tokenize import download_nltk_packages

    for pkg in ("punkt", "averaged_perceptron_tagger", "stopwords"):
        nltk.download(pkg, quiet=True)
    download_nltk_packages()


if __name__ == "__main__":
    main()
