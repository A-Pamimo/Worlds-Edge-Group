from weg import figures


def test_save_svg_png_deterministic(tmp_path):
    def draw(name):
        fig, ax = figures.new_figure()
        ax.plot([1, 2, 3], [1, 3, 2], color=figures.PRIMARY)
        return figures.save(fig, tmp_path, name)

    s1, p1 = draw("a")
    s2, p2 = draw("b")
    assert s1.read_bytes() == s2.read_bytes()
    assert p1.read_bytes() == p2.read_bytes()
    assert b"<title>" not in s1.read_bytes().split(b"<g id=\"axes_1\">")[0]
