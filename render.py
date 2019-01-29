#! /usr/bin/env python

import glob
import hashlib
import jinja2
import markdown2
import os
import shutil
import time
import urllib.request

from urllib.parse import urlparse

from notion.client import *
from notion.block import *
from notion.utils import *

from slugify import slugify

token_v2 = os.getenv("NOTION_TOKEN_V2")

if not token_v2:
	raise Exception("You must define the NOTION_TOKEN_V2 environment variable before running this script.")

client = NotionClient(token_v2=token_v2)

root = client.get_block("https://www.notion.so/learningequality/Notion-home-b82d70274cb74aa8b49bc6088e6a501f")

env = jinja2.Environment(loader=jinja2.FileSystemLoader("./src/"))


def get_block_content(block):
	if isinstance(block, BasicBlock):
		return markdown2.markdown(block.title)
	elif isinstance(block, ImageBlock):
		url = block.display_source
		filename = os.path.basename(urlparse(url).path)
		path = "./build/media/{}-{}".format(hashlib.md5((remove_signed_prefix_as_needed(url) or "").encode()).hexdigest(), filename)
		try:
			if not os.path.isfile(path):
				urllib.request.urlretrieve(url, path)
		except TypeError:
			return ""
		return markdown2.markdown("![]({})".format(path.replace("build/", "")))


def get_page_content(page):
	return "".join([get_block_content(b) for b in page.children])


def get_template(name):
	with open(os.path.join("./src/{}.html".format(name))) as f:
		template = jinja2.Template(f.read())
	return template


def build(clean=False):

	if clean:
		try:
			shutil.rmtree("./build/media")
		except:
			pass
		for path in glob.glob("./build/*.html"):
			try:
				shutil.remove(path)
			except:
				pass

	try:
		os.mkdir("./build/media")
	except:
		pass

	pages = []

	for page in root.children:
		if isinstance(page, PageBlock):
			pages.append({"template": "base.html", "slug": slugify(page.title), "title": page.title, "context": {"html": get_page_content(page)}})
		elif isinstance(page, CollectionViewPageBlock):
			pages.append({"template": "team.html", "slug": slugify(page.title), "title": page.title, "context": {"people": page.views[0].default_query().execute()}})

	for page in pages:
		template = env.get_template(page["template"])
		context = {
			"title": page["title"],
			"pages": pages,
		}
		context.update(page["context"])
		html = template.render(context)
		path = "./build/{}.html".format(page["slug"])
		try:
			with open(path) as f:
				old_html = f.read()
		except:
			old_html = ""
		if html.strip() != old_html.strip():
			print("CHANGED!")
			with open(path, "w") as f:
				f.write(html)

	try:
		shutil.rmtree("./build/assets")
	except:
		pass
	shutil.copytree("./src/assets", "./build/assets")


def build_repeatedly():
	while True: 
	    print("Building...")
	    build()
	    print("Built!")
	    time.sleep(1) 


if __name__ == "__main__":
	build_repeatedly()
