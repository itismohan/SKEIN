from skein.compression import compress

def test_compression_preserves_security_and_code():
    text='''The implementation is basically straightforward.\nWARNING: never log credentials.\n```python\nraise PaymentError()\n```'''
    r=compress(text)
    assert 'credentials' in r.compressed.lower()
    assert 'PaymentError' in r.compressed
    assert r.outcome=='pass'

def test_compression_fallback_on_missing_load_bearing_item(monkeypatch):
    import skein.compression.core as c
    original=c._compress_segment
    monkeypatch.setattr(c,'_compress_segment',lambda _: 'shortened prose')
    text='WARNING: never expose credentials.'
    r=c.compress(text)
    assert r.outcome=='fallback'
    assert r.compressed==text
    monkeypatch.setattr(c,'_compress_segment',original)
