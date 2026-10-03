import math
import os

import pytest

from parallel import run_jobs_in_parallel, default_worker_count

# builtin functions are used as workers because they can be sent to other processes from any test module

def test_results_come_back_in_job_order_whatever_order_the_jobs_finish():
    jobs = [20, 3, 15, 1, 12, 5]

    assert run_jobs_in_parallel(math.factorial, jobs, max_workers = 3) == [math.factorial(j) for j in jobs]

def test_a_single_worker_gives_the_same_results_as_several():
    jobs = [4, 9, 2, 7]

    assert run_jobs_in_parallel(math.factorial, jobs, max_workers = 1) == run_jobs_in_parallel(math.factorial, jobs, max_workers = 3)

def test_no_jobs_gives_no_results():
    assert run_jobs_in_parallel(math.factorial, [], max_workers = 4) == []

def test_more_workers_than_jobs_is_fine():
    assert run_jobs_in_parallel(math.factorial, [3, 4], max_workers = 16) == [6, 24]

def test_a_worker_count_below_one_is_rejected():
    with pytest.raises(ValueError):
        run_jobs_in_parallel(math.factorial, [1], max_workers = 0)

def test_an_error_in_a_worker_is_raised_to_the_caller():
    with pytest.raises(ValueError):
        run_jobs_in_parallel(int, ["12", "not a number"], max_workers = 2)

def test_progress_is_reported_once_per_finished_job(capsys):
    run_jobs_in_parallel(math.factorial, [1, 2, 3], max_workers = 1, progress = True)

    error_output = capsys.readouterr().err
    assert error_output.count("jobs finished") == 3
    assert "[3/3]" in error_output

def test_nothing_is_printed_unless_progress_is_asked_for(capsys):
    run_jobs_in_parallel(math.factorial, [1, 2, 3], max_workers = 1)

    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""

def test_the_default_worker_count_is_between_one_and_the_cpu_count():
    assert 1 <= default_worker_count() <= (os.cpu_count() or 1)
