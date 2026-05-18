import { Component, ErrorInfo, ReactNode } from 'react';
import { Button, Result } from 'antd';
import { withTranslation, WithTranslation } from 'react-i18next';

interface Props extends WithTranslation {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    const { t } = this.props;
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <Result
            status="error"
            title={t('common.somethingWentWrong')}
            subTitle={this.state.error?.message}
            extra={
              <Button type="primary" onClick={this.handleReset}>
                {t('common.tryAgain')}
              </Button>
            }
          />
        )
      );
    }

    return this.props.children;
  }
}

export default withTranslation()(ErrorBoundary);