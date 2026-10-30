"""Unit tests for the eval scorer. No cluster, no model, no network."""
from eval.task_fidelity import compare_results


def item(kind, name, category):
    return {"kind": kind, "name": name, "category": category}


def test_all_correct_passes():
    exp = [item("Pod", "a", "k8s_issue"), item("Pod", "b", "unclear")]
    got = [item("Pod", "b", "unclear"), item("Pod", "a", "k8s_issue")]  # order doesn't matter
    r = compare_results(exp, got)
    assert r["pass"]
    assert sorted(r["correct"]) == [("Pod", "a"), ("Pod", "b")]


def test_each_bucket():
    exp = [item("Pod", "a", "k8s_issue"),   # returned with the right category
           item("Pod", "b", "k8s_issue"),   # returned with the wrong category
           item("Pod", "d", "k8s_issue")]   # not returned
    got = [item("Pod", "a", "k8s_issue"),
           item("Pod", "b", "unclear"),
           item("Pod", "c", "k8s_issue")]   # not expected
    r = compare_results(exp, got)
    assert r["correct"] == [("Pod", "a")]
    assert r["incorrect"] == [("Pod", "b")]
    assert r["missing"] == [("Pod", "d")]
    assert r["false_positives"] == [("Pod", "c")]
    assert not r["pass"]


def test_replicaset_hash_suffix_is_ignored():
    exp = [item("ReplicaSet", "billing", "k8s_issue")]
    got = [item("ReplicaSet", "billing-9bdfc5cbc", "k8s_issue")]
    assert compare_results(exp, got)["pass"]


def test_normal_dashed_names_are_not_merged():
    exp = [item("PersistentVolumeClaim", "reports-data", "k8s_issue")]
    got = [item("PersistentVolumeClaim", "reports-cache", "k8s_issue")]
    r = compare_results(exp, got)
    assert r["missing"] == [("PersistentVolumeClaim", "reports-data")]
    assert r["false_positives"] == [("PersistentVolumeClaim", "reports-cache")]


def test_same_name_different_kind_is_a_different_object():
    exp = [item("Pod", "search", "k8s_issue")]
    got = [item("HorizontalPodAutoscaler", "search", "k8s_issue")]
    assert not compare_results(exp, got)["pass"]


def test_nothing_expected_nothing_returned_passes():
    assert compare_results([], [])["pass"]
