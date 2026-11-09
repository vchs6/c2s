"""每次解析建立一次UTF-8行偏移索引。"""
def line_offsets(source):
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def node_span(node, offsets):
    return (offsets[node.lineno - 1] + node.col_offset,
            offsets[node.end_lineno - 1] + node.end_col_offset)
