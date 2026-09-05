-- Nested .gitmodules graph for grpc/grpc @ 6e5ac36afe
-- (parent_repo, path) -> (child_repo, commit_sha); the commit_sha is the pin.
PRAGMA foreign_keys = ON;

CREATE TABLE repo (
  id             INTEGER PRIMARY KEY,
  slug           TEXT NOT NULL UNIQUE,
  url            TEXT,
  has_gitmodules INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE submodule_pin (
  parent_id  INTEGER NOT NULL REFERENCES repo(id),
  path       TEXT    NOT NULL,
  child_id   INTEGER NOT NULL REFERENCES repo(id),
  commit_sha TEXT,
  PRIMARY KEY (parent_id, path)
);

INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (1, 'Microsoft/vcpkg', 'https://github.com/Microsoft/vcpkg', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (2, 'abseil/abseil-cpp', 'https://github.com/abseil/abseil-cpp.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (3, 'aquynh/capstone', 'https://github.com/aquynh/capstone.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (4, 'c-ares/c-ares', 'https://github.com/c-ares/c-ares.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (5, 'census-instrumentation/opencensus-proto', 'https://github.com/census-instrumentation/opencensus-proto.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (6, 'cncf/xds', 'https://github.com/cncf/xds.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (7, 'envoyproxy/data-plane-api', 'https://github.com/envoyproxy/data-plane-api.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (8, 'envoyproxy/protoc-gen-validate', 'https://github.com/envoyproxy/protoc-gen-validate.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (9, 'google/benchmark', 'https://github.com/google/benchmark', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (10, 'google/bloaty', 'https://github.com/google/bloaty.git', 1);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (11, 'google/boringssl', 'https://github.com/google/boringssl.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (12, 'google/cel-spec', 'https://github.com/google/cel-spec', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (13, 'google/googletest', 'https://github.com/google/googletest.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (14, 'google/re2', 'https://github.com/google/re2', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (15, 'googleapis/googleapis', 'https://github.com/googleapis/googleapis.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (16, 'grpc/grpc', 'https://github.com/grpc/grpc', 1);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (17, 'grpc/grpc-proto', 'https://github.com/grpc/grpc-proto.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (18, 'jupp0r/prometheus-cpp', 'https://github.com/jupp0r/prometheus-cpp', 1);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (19, 'madler/zlib', 'https://github.com/madler/zlib', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (20, 'microsoft/GSL', 'https://github.com/microsoft/GSL', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (21, 'nico/demumble', 'https://github.com/nico/demumble.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (22, 'nlohmann/json', 'https://github.com/nlohmann/json', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (23, 'open-telemetry/opentelemetry-cpp', 'https://github.com/open-telemetry/opentelemetry-cpp', 1);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (24, 'open-telemetry/opentelemetry-proto', 'https://github.com/open-telemetry/opentelemetry-proto.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (25, 'opentracing/opentracing-cpp', 'https://github.com/opentracing/opentracing-cpp.git', 0);
INSERT INTO repo (id, slug, url, has_gitmodules) VALUES (26, 'protocolbuffers/protobuf', 'https://github.com/protocolbuffers/protobuf.git', 1);

INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/abseil-cpp', 2, '76bb24329e8bf5f39704eb10d21b9a80befa7c81');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/benchmark', 9, '12235e24652fc7f809373e7c11a5f73c5763fc4c');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/bloaty', 10, '60209eb1ccc34d5deefb002d1b7f37545204f7f2');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (10, 'third_party/re2', 14, '5bd613749fd530b576b890283bfb6bc6ea6246cb');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (10, 'third_party/googletest', 13, '565f1b848215b77c3732bca345fe76a0431d8b34');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (10, 'third_party/abseil-cpp', 2, '5dd240724366295970c613ed23d0092bcf392f18');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (10, 'third_party/protobuf', 26, 'bc1773c42c9c3c522145a3119e989e0dff2a8d54');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (10, 'third_party/capstone', 3, '852f46a467cb37559a1f3a18bd45d5ca8c6fc5e7');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (10, 'third_party/demumble', 21, '01098eab821b33bd31b9778aea38565cd796aa85');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (10, 'third_party/zlib', 19, 'cacf7f1d4e3d44d871b605da3b647f07d718623f');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/boringssl-with-bazel', 11, '3adc3d1aba162a578e2547f329fcce8659b8e89c');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/cares/cares', 4, 'd3a507e920e7af18a5efb7f9f1d8044ed4750013');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/envoy-api', 7, '6ef568cf4a67362849911d1d2a546fd9f35db2ff');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/googleapis', 15, '2193a2bfcecb92b92aad7a4d81baa428cafd7dfd');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/googletest', 13, '52eb8108c5bdec04579160ae17225d66034bd723');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/opencensus-proto', 5, '4aa53e15cbf1a47bc9087e6cfdca214c1eea4e89');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/opentelemetry', 24, '60fa8754d890b5c55949a8c68dcfd7ab5c2395df');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/protobuf', 26, '35cd01f9fe9afbeea38cc7b979a3b6bfcde82c03');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/protoc-gen-validate', 8, '7b06248484ceeaa947e93ca2747eccf336a88ecc');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/re2', 14, '0c5616df9c0aaa44c9440d87422012423d91c7d1');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/xds', 6, 'ee656c7534f5d7dc23d44dd611689568f72017a6');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/zlib', 19, 'f1f503da85d52e56aae11557b4d79a42bcaa2b86');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/opentelemetry-cpp', 23, 'ced79860f8c8a091a2eabfee6d47783f828a9b59');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (23, 'third_party/prometheus-cpp', 18, 'e5fada43131d251e9c4786b04263ce98b6767ba5');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (23, 'tools/vcpkg', 1, 'fba75d09065fcc76a25dcf386b1d00d33f5175af');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (23, 'third_party/ms-gsl', 20, '6f4529395c5b7c2d661812257cd6780c67e54afa');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (23, 'third_party/googletest', 13, 'f8d7d77c06936315286eb55f8de22cd23c188571');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (23, 'third_party/benchmark', 9, '344117638c8ff7e239044fd0fa7085839fc03021');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (23, 'third_party/opentelemetry-proto', 24, '2bd940b2b77c1ab57c27166af21384906da7bb2b');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (23, 'third_party/nlohmann-json', 22, '9cca280a4d0ccf0c08f47a99aa71d1b0e52f8d03');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (23, 'third_party/opentracing-cpp', 25, '06b57f48ded1fa3bdd3d4346f6ef29e40e08eaf5');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/cel-spec', 12, '9f069b3ee58b02d6f6736c5ebd6587075c1a1b22');
INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES (16, 'third_party/grpc-proto', 17, 'ec30f589e2519d595688b9a42f88a91bdd6b733f');

-- dependencies vendored at more than one commit:
-- SELECT c.slug, COUNT(DISTINCT p.commit_sha) n,
--        GROUP_CONCAT(DISTINCT substr(p.commit_sha,1,7)) commits
-- FROM submodule_pin p JOIN repo c ON c.id = p.child_id
-- GROUP BY c.slug HAVING n > 1 ORDER BY n DESC;
