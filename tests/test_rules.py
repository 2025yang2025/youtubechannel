from src.rules import analyze_rules


def test_rules():

    result = analyze_rules(

        title="台股 AI 半導體展望",

        description=(
            "台積電營收成長 20%。"
        ),

        transcript=(
            "AI 需求持續，"
            "台積電營收成長 20%。"
        ),

        keywords=[
            "台股",
            "AI",
            "台積電",
        ],
    )


    assert (
        result["score"] > 0
    )


    assert (
        result["category"]
        in {
            "台股",
            "AI",
            "半導體",
            "其他",
        }
    )


    assert (
        "台積電"
        in result[
            "mentioned_assets"
        ]
    )
