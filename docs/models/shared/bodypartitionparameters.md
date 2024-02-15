# BodyPartitionParameters


## Fields

| Field                                                                                                                                                                                                                                                                          | Type                                                                                                                                                                                                                                                                           | Required                                                                                                                                                                                                                                                                       | Description                                                                                                                                                                                                                                                                    | Example                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `files`                                                                                                                                                                                                                                                                        | [shared.Files](../../models/shared/files.md)                                                                                                                                                                                                                                   | :heavy_check_mark:                                                                                                                                                                                                                                                             | The file to extract                                                                                                                                                                                                                                                            |                                                                                                                                                                                                                                                                                |
| `chunking_strategy`                                                                                                                                                                                                                                                            | *Optional[Any]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | Use one of the supported strategies to chunk the returned elements. Currently supports: by_title                                                                                                                                                                               |                                                                                                                                                                                                                                                                                |
| `combine_under_n_chars`                                                                                                                                                                                                                                                        | *Optional[int]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If chunking strategy is set, combine elements until a section reaches a length of n chars. Default: 500                                                                                                                                                                        |                                                                                                                                                                                                                                                                                |
| `coordinates`                                                                                                                                                                                                                                                                  | *Optional[bool]*                                                                                                                                                                                                                                                               | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If true, return coordinates for each element. Default: false                                                                                                                                                                                                                   |                                                                                                                                                                                                                                                                                |
| `encoding`                                                                                                                                                                                                                                                                     | *Optional[str]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | The encoding method used to decode the text input. Default: utf-8                                                                                                                                                                                                              |                                                                                                                                                                                                                                                                                |
| `extract_image_block_types`                                                                                                                                                                                                                                                    | List[*str*]                                                                                                                                                                                                                                                                    | :heavy_minus_sign:                                                                                                                                                                                                                                                             | The types of elements to extract, for use in extracting image blocks as base64 encoded data stored in metadata fields                                                                                                                                                          |                                                                                                                                                                                                                                                                                |
| `gz_uncompressed_content_type`                                                                                                                                                                                                                                                 | *Optional[str]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If file is gzipped, use this content type after unzipping                                                                                                                                                                                                                      |                                                                                                                                                                                                                                                                                |
| `hi_res_model_name`                                                                                                                                                                                                                                                            | *Optional[str]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | The name of the inference model used when strategy is hi_res                                                                                                                                                                                                                   |                                                                                                                                                                                                                                                                                |
| `include_page_breaks`                                                                                                                                                                                                                                                          | *Optional[bool]*                                                                                                                                                                                                                                                               | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If True, the output will include page breaks if the filetype supports it. Default: false                                                                                                                                                                                       |                                                                                                                                                                                                                                                                                |
| `languages`                                                                                                                                                                                                                                                                    | List[*str*]                                                                                                                                                                                                                                                                    | :heavy_minus_sign:                                                                                                                                                                                                                                                             | The languages present in the document, for use in partitioning and/or OCR                                                                                                                                                                                                      |                                                                                                                                                                                                                                                                                |
| `max_characters`                                                                                                                                                                                                                                                               | *Optional[int]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If chunking strategy is set, cut off new sections after reaching a length of n chars (hard max). Default: 1500                                                                                                                                                                 |                                                                                                                                                                                                                                                                                |
| `multipage_sections`                                                                                                                                                                                                                                                           | *Optional[bool]*                                                                                                                                                                                                                                                               | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If chunking strategy is set, determines if sections can span multiple sections. Default: true                                                                                                                                                                                  |                                                                                                                                                                                                                                                                                |
| `new_after_n_chars`                                                                                                                                                                                                                                                            | *Optional[int]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If chunking strategy is set, cut off new sections after reaching a length of n chars (soft max). Default: 1500                                                                                                                                                                 |                                                                                                                                                                                                                                                                                |
| `ocr_languages`                                                                                                                                                                                                                                                                | List[*str*]                                                                                                                                                                                                                                                                    | :heavy_minus_sign:                                                                                                                                                                                                                                                             | The languages present in the document, for use in partitioning and/or OCR                                                                                                                                                                                                      |                                                                                                                                                                                                                                                                                |
| `output_format`                                                                                                                                                                                                                                                                | *Optional[str]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | The format of the response. Supported formats are application/json and text/csv. Default: application/json.                                                                                                                                                                    |                                                                                                                                                                                                                                                                                |
| `overlap`                                                                                                                                                                                                                                                                      | *Optional[int]*                                                                                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                                                                                             | Specifies the length of a string ('tail') to be drawn from each chunk and prefixed to the next chunk as a context-preserving mechanism. By default, this only applies to split-chunks where an oversized element is divided into multiple chunks by text-splitting. Default: 0 |                                                                                                                                                                                                                                                                                |
| `overlap_all`                                                                                                                                                                                                                                                                  | *Optional[bool]*                                                                                                                                                                                                                                                               | :heavy_minus_sign:                                                                                                                                                                                                                                                             | When `True`, apply overlap between 'normal' chunks formed from whole elements and not subject to text-splitting. Use this with caution as it entails a certain level of 'pollution' of otherwise clean semantic chunk boundaries. Default: False                               |                                                                                                                                                                                                                                                                                |
| `pdf_infer_table_structure`                                                                                                                                                                                                                                                    | *Optional[bool]*                                                                                                                                                                                                                                                               | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If True and strategy=hi_res, any Table Elements extracted from a PDF will include an additional metadata field, 'text_as_html', where the value (string) is a just a transformation of the data into an HTML <table>.                                                          |                                                                                                                                                                                                                                                                                |
| `skip_infer_table_types`                                                                                                                                                                                                                                                       | List[*str*]                                                                                                                                                                                                                                                                    | :heavy_minus_sign:                                                                                                                                                                                                                                                             | The document types that you want to skip table extraction with. Default: ['pdf', 'jpg', 'png']                                                                                                                                                                                 |                                                                                                                                                                                                                                                                                |
| `strategy`                                                                                                                                                                                                                                                                     | [Optional[shared.Strategy]](../../models/shared/strategy.md)                                                                                                                                                                                                                   | :heavy_minus_sign:                                                                                                                                                                                                                                                             | The strategy to use for partitioning PDF/image. Options are fast, hi_res, auto. Default: auto                                                                                                                                                                                  | auto                                                                                                                                                                                                                                                                           |
| `xml_keep_tags`                                                                                                                                                                                                                                                                | *Optional[bool]*                                                                                                                                                                                                                                                               | :heavy_minus_sign:                                                                                                                                                                                                                                                             | If True, will retain the XML tags in the output. Otherwise it will simply extract the text from within the tags. Only applies to partition_xml.                                                                                                                                |                                                                                                                                                                                                                                                                                |