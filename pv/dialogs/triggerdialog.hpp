/*
 * This file is part of the LogicAnalyzer project.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#ifndef PULSEVIEW_PV_DIALOGS_TRIGGERDIALOG_HPP
#define PULSEVIEW_PV_DIALOGS_TRIGGERDIALOG_HPP

#include <QDialog>
#include <QVector>

#include <memory>
#include <vector>

class QComboBox;
class QLabel;
class QRadioButton;
class QSlider;
class QSpinBox;
class QTabWidget;

namespace sigrok {
class Trigger;
}

namespace pv {

class Session;

namespace data {
class SignalBase;
}

namespace dialogs {

class TriggerDialog : public QDialog
{
	Q_OBJECT

public:
	explicit TriggerDialog(Session &session, QWidget *parent = nullptr);

private Q_SLOTS:
	void onModeChanged();
	void onStagesChanged();
	void applyTrigger();

private:
	void buildUi();
	void rebuildStageTabs();
	void loadTriggerIntoStages(std::shared_ptr<sigrok::Trigger> trigger);
	void loadCurrentTrigger();
	void updateAdvancedState();

	Session &session_;
	std::vector<std::shared_ptr<data::SignalBase>> logic_channels_;

	QRadioButton *simple_radio_;
	QRadioButton *advanced_radio_;
	QSpinBox *position_spin_;
	QSlider *position_slider_;
	QSpinBox *stages_spin_;
	QTabWidget *stage_tabs_;
	QTabWidget *mode_tabs_;

	QVector<QVector<QComboBox *>> stage_combos_;
	bool loading_;
};

} // namespace dialogs
} // namespace pv

#endif // PULSEVIEW_PV_DIALOGS_TRIGGERDIALOG_HPP
