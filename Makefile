.PHONY: setup start stop restart check qa cs fix test audit doctor reset diagnose perf

PROJECT ?= sympress-starter

setup:
	bin/console setup $(PROJECT)

start:
	ddev start

stop:
	ddev stop

restart:
	ddev restart

check:
	bin/console check

qa:
	ddev composer qa

cs:
	ddev composer cs

fix:
	ddev composer cs:fix

test:
	ddev composer test

audit:
	ddev composer audit --locked --no-interaction

doctor:
	bin/console doctor

reset:
	bin/console reset --yes $(PROJECT)

diagnose:
	bin/console diagnose-login

perf:
	bin/console perf
