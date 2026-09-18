import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_batch_id():
    from extract.who_covid_extractor import generate_batch_id
    b = generate_batch_id()
    assert b.startswith('batch_')
