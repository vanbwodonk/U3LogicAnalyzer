/*
 * This file is part of the LogicAnalyzer project.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#include "triggerdialog.hpp"

#include <QComboBox>
#include <QDialogButtonBox>
#include <QFormLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QLabel>
#include <QMessageBox>
#include <QRadioButton>
#include <QSlider>
#include <QSpinBox>
#include <QTabWidget>
#include <QVBoxLayout>

#include <algorithm>

#include <libsigrokcxx/libsigrokcxx.hpp>

#include <pv/data/signalbase.hpp>
#include <pv/devicemanager.hpp>
#include <pv/devices/device.hpp>
#include <pv/session.hpp>

using std::shared_ptr;
using sigrok::ConfigKey;
using sigrok::TriggerMatchType;

namespace pv {
namespace dialogs {

namespace {

const int TriggerMatchValues[] = {
	SR_TRIGGER_ZERO,
	SR_TRIGGER_ONE,
	SR_TRIGGER_RISING,
	SR_TRIGGER_FALLING,
	SR_TRIGGER_EDGE,
};

QString triggerValueText(int match)
{
	switch (match) {
	case SR_TRIGGER_ZERO:
		return "0";
	case SR_TRIGGER_ONE:
		return "1";
	case SR_TRIGGER_RISING:
		return "R";
	case SR_TRIGGER_FALLING:
		return "F";
	case SR_TRIGGER_EDGE:
		return "C";
	default:
		return "X";
	}
}

} // namespace

TriggerDialog::TriggerDialog(Session &session, QWidget *parent) :
	QDialog(parent),
	session_(session),
	simple_radio_(nullptr),
	advanced_radio_(nullptr),
	position_spin_(nullptr),
	position_slider_(nullptr),
	stages_spin_(nullptr),
	stage_tabs_(nullptr),
	mode_tabs_(nullptr),
	loading_(false)
{
	setWindowTitle(tr("Trigger Option"));

	for (const shared_ptr<data::SignalBase> &signal : session_.signalbases()) {
		if (signal->type() == data::SignalBase::LogicChannel)
			logic_channels_.push_back(signal);
	}
	std::sort(logic_channels_.begin(), logic_channels_.end(),
		[](const shared_ptr<data::SignalBase> &a,
		   const shared_ptr<data::SignalBase> &b) {
			return a->index() < b->index();
		});

	buildUi();
	loadCurrentTrigger();
}

void TriggerDialog::buildUi()
{
	QVBoxLayout *root = new QVBoxLayout(this);

	simple_radio_ = new QRadioButton(tr("Simple Trigger"), this);
	advanced_radio_ = new QRadioButton(tr("Advanced Trigger"), this);
	simple_radio_->setChecked(true);
	root->addWidget(simple_radio_);
	root->addWidget(advanced_radio_);

	QHBoxLayout *position_layout = new QHBoxLayout();
	position_layout->addWidget(new QLabel(tr("Trigger Position:"), this));
	position_spin_ = new QSpinBox(this);
	position_spin_->setRange(1, 100);
	position_spin_->setSuffix(" %");
	position_layout->addWidget(position_spin_);
	position_layout->addStretch(1);
	root->addLayout(position_layout);

	position_slider_ = new QSlider(Qt::Horizontal, this);
	position_slider_->setRange(1, 100);
	root->addWidget(position_slider_);
	connect(position_spin_, QOverload<int>::of(&QSpinBox::valueChanged),
		position_slider_, &QSlider::setValue);
	connect(position_slider_, &QSlider::valueChanged,
		position_spin_, &QSpinBox::setValue);

	QHBoxLayout *stages_layout = new QHBoxLayout();
	stages_layout->addWidget(new QLabel(tr("Total Trigger Stages:"), this));
	stages_spin_ = new QSpinBox(this);
	stages_spin_->setRange(1, 16);
	stages_layout->addWidget(stages_spin_);
	stages_layout->addStretch(1);
	root->addLayout(stages_layout);

	mode_tabs_ = new QTabWidget(this);
	stage_tabs_ = new QTabWidget(this);

	QWidget *stage_page = new QWidget(this);
	QVBoxLayout *stage_layout = new QVBoxLayout(stage_page);
	stage_layout->addWidget(stage_tabs_);
	QLabel *legend = new QLabel(tr(
		"X: Don't care\n"
		"0: Low level\n"
		"1: High level\n"
		"R: Rising edge\n"
		"F: Falling edge\n"
		"C: Rising/Falling edge"), stage_page);
	stage_layout->addWidget(legend);
	mode_tabs_->addTab(stage_page, tr("Stage Trigger"));

	QWidget *serial_page = new QWidget(this);
	QVBoxLayout *serial_layout = new QVBoxLayout(serial_page);
	QLabel *serial_note = new QLabel(tr(
		"Serial Trigger is not supported by the current libsigrok "
		"DSLogic driver."), serial_page);
	serial_note->setWordWrap(true);
	serial_layout->addWidget(serial_note);
	serial_layout->addStretch(1);
	mode_tabs_->addTab(serial_page, tr("Serial Trigger"));
	mode_tabs_->setTabEnabled(1, false);

	root->addWidget(mode_tabs_);

	QDialogButtonBox *buttons = new QDialogButtonBox(
		QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
	connect(buttons, &QDialogButtonBox::accepted, this, [this]() {
		applyTrigger();
	});
	connect(buttons, &QDialogButtonBox::rejected, this, &QDialog::reject);
	root->addWidget(buttons);

	connect(simple_radio_, &QRadioButton::toggled,
		this, &TriggerDialog::onModeChanged);
	connect(advanced_radio_, &QRadioButton::toggled,
		this, &TriggerDialog::onModeChanged);
	connect(stages_spin_, QOverload<int>::of(&QSpinBox::valueChanged),
		this, &TriggerDialog::onStagesChanged);
}

void TriggerDialog::rebuildStageTabs()
{
	const int stages = stages_spin_->value();
	stage_tabs_->clear();
	stage_combos_.clear();

	for (int stage = 0; stage < stages; ++stage) {
		QWidget *page = new QWidget(stage_tabs_);
		QGridLayout *layout = new QGridLayout(page);

		QVector<QComboBox *> combos(logic_channels_.size(), nullptr);
		for (int i = 0; i < logic_channels_.size(); ++i) {
			const int channel = logic_channels_[i]->index();
			if (channel < 0 || channel >= 16)
				continue;

			QComboBox *combo = new QComboBox(page);
			combo->addItem("X", -1);
			for (int match : TriggerMatchValues)
				combo->addItem(triggerValueText(match), match);
			combos[i] = combo;

			QLabel *label = new QLabel(QString::number(channel), page);
			label->setAlignment(Qt::AlignCenter);
			layout->addWidget(label, 0, channel);
			layout->addWidget(combo, 1, channel);
		}

		stage_combos_.push_back(combos);
		stage_tabs_->addTab(page, tr("Stage %1").arg(stage + 1));
	}
}

void TriggerDialog::loadCurrentTrigger()
{
	loading_ = true;

	const shared_ptr<sigrok::Device> device = session_.device() ?
		session_.device()->device() : nullptr;
	if (device && device->config_check(ConfigKey::CAPTURE_RATIO,
			sigrok::Capability::GET)) {
		try {
			const auto value = device->config_get(ConfigKey::CAPTURE_RATIO);
			position_spin_->setValue((int)Glib::VariantBase::cast_dynamic<Glib::Variant<guint64>>(value).get());
		} catch (sigrok::Error &) {
			position_spin_->setValue(1);
		}
	} else {
		position_spin_->setValue(1);
	}

	shared_ptr<sigrok::Trigger> trigger = session_.session()->trigger();
	const int stage_count = trigger ?
		(int)trigger->stages().size() : 1;

	stages_spin_->setValue(std::max(1, std::min(16, stage_count)));
	rebuildStageTabs();

	int stage_index = 0;
	if (trigger) {
		for (const shared_ptr<sigrok::TriggerStage> &stage : trigger->stages()) {
			if (stage_index >= stage_combos_.size())
				break;
			for (const shared_ptr<sigrok::TriggerMatch> &match :
					stage->matches()) {
				for (int i = 0; i < logic_channels_.size(); ++i) {
					if (logic_channels_[i]->channel() == match->channel()) {
						if (stage_combos_[stage_index][i]) {
							const int index = stage_combos_[stage_index][i]->findData(
								match->type()->id());
							if (index >= 0)
								stage_combos_[stage_index][i]->setCurrentIndex(index);
						}
						break;
					}
				}
			}
			stage_index++;
		}
	}

	advanced_radio_->setChecked(stage_count > 1);
	simple_radio_->setChecked(stage_count <= 1);
	loading_ = false;
	updateAdvancedState();
}

void TriggerDialog::onModeChanged()
{
	if (loading_)
		return;

	if (advanced_radio_->isChecked() && session_.device()) {
		const shared_ptr<sigrok::Device> device = session_.device()->device();
		if (device && device->config_check(ConfigKey::CONTINUOUS,
				sigrok::Capability::GET)) {
			try {
				const auto value = device->config_get(ConfigKey::CONTINUOUS);
				if (Glib::VariantBase::cast_dynamic<Glib::Variant<bool>>(value).get()) {
					QMessageBox::information(this, tr("Trigger Option"),
						tr("Advanced Trigger is not available in Stream mode."));
					simple_radio_->setChecked(true);
					return;
				}
			} catch (sigrok::Error &) {
			}
		}
	}

	updateAdvancedState();
}

void TriggerDialog::onStagesChanged()
{
	if (loading_)
		return;
	rebuildStageTabs();
}

void TriggerDialog::updateAdvancedState()
{
	const bool advanced = advanced_radio_->isChecked();
	stages_spin_->setEnabled(advanced);
	mode_tabs_->setTabEnabled(0, true);
	mode_tabs_->setTabEnabled(1, false);

	if (!advanced && stages_spin_->value() != 1)
		stages_spin_->setValue(1);
}

void TriggerDialog::applyTrigger()
{
	const shared_ptr<sigrok::Device> device = session_.device() ?
		session_.device()->device() : nullptr;
	if (!device) {
		reject();
		return;
	}

	const int stage_count = advanced_radio_->isChecked() ?
		stages_spin_->value() : 1;
	const int pages = std::min(stage_count, (int)stage_combos_.size());

	auto context = session_.device_manager().context();
	auto trigger = context->create_trigger("U3LogicAnalyzer");

	for (int s = 0; s < pages; ++s) {
		bool has_match = false;
		for (int i = 0; i < logic_channels_.size(); ++i) {
			QComboBox *combo = stage_combos_[s][i];
			if (combo && combo->currentData().toInt() >= 0) {
				has_match = true;
				break;
			}
		}
		if (!has_match)
			continue;

		auto stage = trigger->add_stage();
		for (int i = 0; i < logic_channels_.size(); ++i) {
			QComboBox *combo = stage_combos_[s][i];
			if (!combo)
				continue;
			const int match_id = combo->currentData().toInt();
			if (match_id < 0)
				continue;

			const TriggerMatchType *type = TriggerMatchType::get(match_id);
			if (type)
				stage->add_match(logic_channels_[i]->channel(), type);
		}
	}

	session_.session()->set_trigger(
		trigger->stages().empty() ? nullptr : trigger);

	if (device->config_check(ConfigKey::CAPTURE_RATIO,
			sigrok::Capability::SET)) {
		try {
			device->config_set(ConfigKey::CAPTURE_RATIO,
				Glib::Variant<guint64>::create(position_spin_->value()));
		} catch (sigrok::Error &e) {
			QMessageBox::warning(this, tr("Trigger Option"),
				tr("Failed to set trigger position: %1").arg(e.what()));
			return;
		}
	}

	accept();
}

} // namespace dialogs
} // namespace pv
